#!/usr/bin/env python3
"""
ingest_watchdog.py - Continuous background ingestion daemon (Paperless API version)
Polls Paperless-NGX for new documents, extracts text via OCR + targeted VLM for
image-heavy pages, embeds with Infinity, stores in Qdrant universal_knowledge.

Architecture:
  Paperless API → OCR text (per page via PyMuPDF)
                → VLM (minicpm-v) only for image-heavy pages
                → Infinity embed (mxbai-embed-large-v1, 1024-dim)
                → Qdrant universal_knowledge

Run: python3 /home/node/clawd/ingest_watchdog.py
"""

import os
import io
import sys
import json
import time
import base64
import hashlib
import requests
import traceback
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
STATE_FILE     = "/home/node/clawd/ingest_watchdog_state.json"
LOG_FILE       = "/home/node/clawd/ingest_watchdog.log"

PAPERLESS_URL  = "http://paperless:8000"
PAPERLESS_TOKEN = "a451ceb5c13ac270faf3936405d207e4093ff580"

OLLAMA_URL     = "http://ollama:11434/api/generate"
INFINITY_URL   = "http://infinity:7997/embeddings"
QDRANT_URL     = "http://qdrant:6333"
DOCLING_URL    = os.getenv("DOCLING_URL", "http://docling:5001")
COLLECTION     = "universal_knowledge"

VLM_MODEL      = "minicpm-v:latest"
EMBED_MODEL    = "mixedbread-ai/mxbai-embed-large-v1"
EMBED_DIM      = 1024

# Pages with fewer than this many characters are considered image-heavy → use VLM
IMAGE_PAGE_THRESHOLD = 100

# Chunk size for embedding
CHUNK_SIZE     = 800

# Max pages per document (None = no limit)
MAX_PAGES      = 60

# Seconds to sleep between poll cycles
IDLE_SLEEP     = 120

# Paperless API headers
HEADERS        = {"Authorization": f"Token {PAPERLESS_TOKEN}"}

# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    # When stdout is a TTY (interactive), print to console only.
    # When redirected to file (daemon), write directly to log file only — avoids duplicates.
    if sys.stdout.isatty():
        print(line, flush=True)
    else:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

# ── State management ───────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": {}}  # {str(doc_id): {"title": ..., "pages": ..., "chunks": ..., "ts": ...}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ── Paperless API ──────────────────────────────────────────────────────────────
def fetch_all_docs(state):
    """Fetch IDs+metadata of all documents not yet in state, ordered by ID."""
    processed = state.get("processed", {})
    new_docs = []
    url = f"{PAPERLESS_URL}/api/documents/?page_size=100&ordering=id"
    while url:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log(f"Paperless list error: {e}", "ERROR")
            break
        for doc in data.get("results", []):
            doc_id = str(doc["id"])
            if doc_id not in processed:
                new_docs.append({
                    "id":          doc["id"],
                    "title":       doc.get("title", ""),
                    "created":     doc.get("created", ""),
                    "added":       doc.get("added", ""),
                    "page_count":  doc.get("page_count", 0),
                })
        url = data.get("next")  # None when last page
    return new_docs

def fetch_doc_detail(doc_id):
    """Fetch full document detail including OCR content."""
    try:
        resp = requests.get(
            f"{PAPERLESS_URL}/api/documents/{doc_id}/",
            headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log(f"  Paperless detail error (id={doc_id}): {e}", "WARN")
        return None

def download_pdf(doc_id):
    """Download PDF bytes for a document."""
    try:
        resp = requests.get(
            f"{PAPERLESS_URL}/api/documents/{doc_id}/download/",
            headers=HEADERS, timeout=60
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        log(f"  Paperless download error (id={doc_id}): {e}", "WARN")
        return None

# ── Docling PDF → Markdown (v1 API) ───────────────────────────────────────────
def extract_text_docling(doc_id: int) -> str | None:
    """
    Paperless PDF を Docling v1 で Markdown に変換して構造化テキストを取得。
    失敗時は None を返し、PyMuPDF パスへフォールバックする。
    優先度: Docling (最高品質) > PyMuPDF > VLM (最終手段)

    Docling v1 API:
      POST /v1/convert/source
      body: {"sources": [{"kind": "http", "url": "...", "headers": {...}}],
             "options": {"to_formats": ["md"]}}
      response: {"output": [{"markdown": "..."}], ...}
    """
    pdf_url = f"{PAPERLESS_URL}/api/documents/{doc_id}/download/"
    try:
        resp = requests.post(
            f"{DOCLING_URL}/v1/convert/source",
            json={
                "sources": [{
                    "kind": "http",
                    "url": pdf_url,
                    "headers": {"Authorization": f"Token {PAPERLESS_TOKEN}"},
                }],
                "options": {
                    "to_formats": ["md"],
                    "do_ocr": True,
                    "force_ocr": False,
                    "include_images": False,  # テキスト抽出のみ (速度優先)
                },
            },
            timeout=300,  # 大きなPDFは時間がかかる
        )
        resp.raise_for_status()
        result = resp.json()
        # Docling v1 レスポンス: output[].markdown
        for item in result.get("output", []):
            md = item.get("markdown", "").strip()
            if md:
                return md
        # フォールバック: document.export_results (旧形式)
        doc_result = result.get("document", {})
        for item in doc_result.get("export_results", []):
            if item.get("format") == "md":
                content = item.get("content", "").strip()
                if content:
                    return content
        return None
    except Exception as e:
        log(f"  Docling failed (id={doc_id}): {e}", "WARN")
        return None


# ── PDF page extraction (PyMuPDF) ──────────────────────────────────────────────
def extract_pdf_pages(pdf_bytes, max_pages=MAX_PAGES):
    """
    Extract per-page text and PNG thumbnails from PDF bytes.
    Returns list of {"index": int, "total": int, "text": str, "png": bytes}.
    """
    try:
        import fitz
    except ImportError:
        log("PyMuPDF not installed — cannot extract PDF pages", "ERROR")
        return []

    pages = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total = len(doc)
        limit = min(total, max_pages) if max_pages else total
        for i in range(limit):
            page = doc[i]
            text = page.get_text("text").strip()
            # Only render PNG if page is image-heavy (saves memory)
            png_bytes = None
            if len(text) < IMAGE_PAGE_THRESHOLD:
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                png_bytes = pix.tobytes("png")
            pages.append({
                "index": i,
                "total": total,
                "text":  text,
                "png":   png_bytes,
            })
        doc.close()
    except Exception as e:
        log(f"  PDF extract error: {e}", "WARN")
    return pages

# ── VLM analysis (minicpm-v) ───────────────────────────────────────────────────
def analyze_page_with_vlm(png_bytes, page_idx, total_pages, doc_title):
    """Send an image-heavy page to minicpm-v for full content extraction."""
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    prompt = (
        f"You are analyzing page {page_idx+1} of {total_pages} from a technical document: '{doc_title}'.\n"
        "Extract ALL information visible on this page:\n"
        "1. All text (transcribe accurately, including headings)\n"
        "2. Tables: describe column headers and all data rows\n"
        "3. Diagrams/figures: describe the structure, labels, and key values\n"
        "4. Formulas or equations: transcribe exactly\n"
        "5. Callouts, notes, legends\n"
        "Do not summarize. Transcribe completely."
    )
    payload = {
        "model": VLM_MODEL,
        "prompt": prompt,
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1500},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        log(f"  VLM error page {page_idx+1}: {e}", "WARN")
        return ""

# ── Embedding ──────────────────────────────────────────────────────────────────
def embed_text(text):
    """Embed text via Infinity (mxbai-embed-large-v1, 1024-dim)."""
    try:
        resp = requests.post(
            INFINITY_URL,
            json={"model": EMBED_MODEL, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        log(f"  Embed error: {e}", "WARN")
        return None

# ── Qdrant upsert ──────────────────────────────────────────────────────────────
def upsert_to_qdrant(point_id, vector, payload_data):
    """Upsert a single point into Qdrant."""
    try:
        resp = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload_data}]},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log(f"  Qdrant upsert error: {e}", "WARN")
        return False

def make_point_id(doc_id, page_idx, chunk_idx):
    """Stable numeric point ID from (doc_id, page, chunk)."""
    raw = f"paperless::{doc_id}::p{page_idx}::c{chunk_idx}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:15], 16)

# ── Process one document ───────────────────────────────────────────────────────
def process_document(doc_meta, state):
    doc_id    = doc_meta["id"]
    doc_title = doc_meta["title"] or f"doc_{doc_id}"
    log(f"Processing doc {doc_id}: {doc_title!r}")

    # ── Step 1: get full detail (OCR content + tags) ──
    detail = fetch_doc_detail(doc_id)
    if not detail:
        state["processed"][str(doc_id)] = {
            "title": doc_title, "error": "fetch_detail_failed",
            "ts": datetime.now().isoformat()
        }
        save_state(state)
        return

    ocr_content = (detail.get("content") or "").strip()
    raw_tags    = detail.get("tags", [])
    # Paperless returns tags as int IDs in the detail endpoint
    tags        = [str(t) if isinstance(t, int) else t.get("name", str(t)) for t in raw_tags]
    created     = detail.get("created", "")
    total_pages = detail.get("page_count") or doc_meta.get("page_count") or 1

    # ── Step 2a: Docling structured Markdown extraction (P4, best quality) ──
    docling_text = extract_text_docling(doc_id)
    if docling_text and len(docling_text) > 200:
        log(f"  Docling OK ({len(docling_text)} chars) — skipping PyMuPDF/VLM")
        ingested = _ingest_raw_text(docling_text, doc_id, doc_title, tags, created)
        state["processed"][str(doc_id)] = {
            "title":  doc_title,
            "pages":  1,
            "chunks": ingested,
            "method": "docling",
            "ts":     datetime.now().isoformat(),
        }
        save_state(state)
        return

    # ── Step 2b: download PDF for per-page processing (fallback) ──
    pdf_bytes = download_pdf(doc_id)
    if not pdf_bytes:
        # Fallback: embed the whole OCR content as one chunk if PDF unavailable
        if ocr_content:
            log(f"  PDF unavailable — falling back to full OCR text ({len(ocr_content)} chars)")
            ingested = _ingest_raw_text(ocr_content, doc_id, doc_title, tags, created)
            state["processed"][str(doc_id)] = {
                "title": doc_title, "pages": 1, "chunks": ingested,
                "ts": datetime.now().isoformat()
            }
        else:
            state["processed"][str(doc_id)] = {
                "title": doc_title, "error": "no_content", "ts": datetime.now().isoformat()
            }
        save_state(state)
        return

    # ── Step 3: extract per-page text (+ PNG for image-heavy pages) ──
    pages = extract_pdf_pages(pdf_bytes, max_pages=MAX_PAGES)
    if not pages:
        # PyMuPDF unavailable — fall back to full OCR blob
        if ocr_content:
            log(f"  PyMuPDF unavailable — using full OCR blob ({len(ocr_content)} chars)")
            ingested = _ingest_raw_text(ocr_content, doc_id, doc_title, tags, created)
            state["processed"][str(doc_id)] = {
                "title": doc_title, "pages": 1, "chunks": ingested,
                "ts": datetime.now().isoformat()
            }
        else:
            state["processed"][str(doc_id)] = {
                "title": doc_title, "error": "no_pages", "ts": datetime.now().isoformat()
            }
        save_state(state)
        return

    # ── Step 4: per-page ingestion ──
    ingested = 0
    for pg in pages:
        idx       = pg["index"]
        page_text = pg["text"]
        png_bytes = pg["png"]  # None if page was text-heavy (not rendered)

        if len(page_text) >= IMAGE_PAGE_THRESHOLD:
            content = f"[Page {idx+1}/{pg['total']}]\n{page_text}"
        elif png_bytes:
            log(f"  Page {idx+1}/{pg['total']}: image-heavy → VLM")
            vlm_out = analyze_page_with_vlm(png_bytes, idx, pg["total"], doc_title)
            content = f"[Page {idx+1}/{pg['total']} — VLM]\n{vlm_out}" if vlm_out else ""
            time.sleep(0.5)  # pace VLM to avoid OOM
        else:
            content = ""  # sparse text but no PNG (should not happen)

        if not content.strip():
            continue

        # Chunk and embed
        chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
        for chunk_idx, chunk in enumerate(chunks):
            vector = embed_text(chunk)
            if not vector or len(vector) != EMBED_DIM:
                continue
            point_id = make_point_id(doc_id, idx, chunk_idx)
            payload  = {
                "source":       f"paperless/{doc_id}/{doc_title}",
                "paperless_id": doc_id,
                "title":        doc_title,
                "page":         idx + 1,
                "chunk":        chunk_idx,
                "content":      chunk,
                "tags":         tags,
                "created":      created,
                "ingested_at":  datetime.now().isoformat(),
            }
            if upsert_to_qdrant(point_id, vector, payload):
                ingested += 1

    log(f"  ✓ doc {doc_id} ({doc_title!r}): {len(pages)} pages → {ingested} chunks")
    state["processed"][str(doc_id)] = {
        "title":  doc_title,
        "pages":  len(pages),
        "chunks": ingested,
        "ts":     datetime.now().isoformat(),
    }
    save_state(state)

def _ingest_raw_text(text, doc_id, doc_title, tags, created):
    """Fallback: embed full OCR text as chunks (no per-page split)."""
    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    ingested = 0
    for chunk_idx, chunk in enumerate(chunks):
        vector = embed_text(chunk)
        if not vector or len(vector) != EMBED_DIM:
            continue
        point_id = make_point_id(doc_id, 0, chunk_idx)
        payload  = {
            "source":       f"paperless/{doc_id}/{doc_title}",
            "paperless_id": doc_id,
            "title":        doc_title,
            "page":         1,
            "chunk":        chunk_idx,
            "content":      chunk,
            "tags":         tags,
            "created":      created,
            "ingested_at":  datetime.now().isoformat(),
        }
        if upsert_to_qdrant(point_id, vector, payload):
            ingested += 1
    return ingested

# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("ingest_watchdog.py started (Paperless API mode)")
    log(f"  PAPERLESS   : {PAPERLESS_URL}")
    log(f"  COLLECTION  : {COLLECTION}")
    log(f"  VLM model   : {VLM_MODEL}")
    log(f"  Embed model : {EMBED_MODEL}")
    log(f"  Chunk size  : {CHUNK_SIZE}  |  Max pages: {MAX_PAGES}")
    log("=" * 60)

    state = load_state()
    already = len(state["processed"])
    log(f"State loaded: {already} document(s) already processed")

    while True:
        try:
            new_docs = fetch_all_docs(state)
            if new_docs:
                log(f"Found {len(new_docs)} new document(s) to process")
                for doc_meta in new_docs:
                    try:
                        process_document(doc_meta, state)
                    except Exception as e:
                        doc_id = doc_meta["id"]
                        log(f"  ERROR processing doc {doc_id}: {e}", "ERROR")
                        log(traceback.format_exc(), "ERROR")
                        state["processed"][str(doc_id)] = {
                            "title": doc_meta.get("title", ""),
                            "error": str(e),
                            "ts":    datetime.now().isoformat(),
                        }
                        save_state(state)
            else:
                log(f"No new documents. Sleeping {IDLE_SLEEP}s...")

        except Exception as e:
            log(f"Main loop error: {e}", "ERROR")
            log(traceback.format_exc(), "ERROR")

        time.sleep(IDLE_SLEEP)

def acquire_pid_lock():
    """Ensure only one instance runs. Returns False if another instance is alive."""
    pid_file = "/home/node/clawd/ingest_watchdog.pid"
    my_pid = os.getpid()
    if os.path.exists(pid_file):
        try:
            old_pid = int(open(pid_file).read().strip())
            # Check if process is still alive
            os.kill(old_pid, 0)
            log(f"Another instance already running (PID {old_pid}). Exiting.", "WARNING")
            return False
        except (ProcessLookupError, ValueError):
            log(f"Stale PID file found. Overwriting.", "INFO")
    with open(pid_file, "w") as f:
        f.write(str(my_pid))
    log(f"PID lock acquired (PID {my_pid})")
    return True

def release_pid_lock():
    pid_file = "/home/node/clawd/ingest_watchdog.pid"
    try:
        if os.path.exists(pid_file):
            stored = int(open(pid_file).read().strip())
            if stored == os.getpid():
                os.remove(pid_file)
    except Exception:
        pass

if __name__ == "__main__":
    if not acquire_pid_lock():
        sys.exit(1)
    import atexit, signal
    atexit.register(release_pid_lock)
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    main()
