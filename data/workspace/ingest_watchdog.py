#!/usr/bin/env python3
"""
ingest_watchdog.py - Continuous Paperless ingestion daemon

Polls Paperless-NGX for new documents, routes PDFs by type, extracts text with
Docling / PyMuPDF / targeted VLM, embeds with Infinity, and stores records in
Qdrant universal_knowledge.
"""

from __future__ import annotations

import atexit
import base64
import hashlib
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests


STATE_FILE = "/home/node/clawd/ingest_watchdog_state.json"
LOG_FILE = "/home/node/clawd/ingest_watchdog.log"
STATUS_FILE = "/home/node/clawd/ingest_watchdog_status.json"
PID_FILE = "/home/node/clawd/ingest_watchdog.pid"
FIGURE_ASSET_DIR = "/home/node/clawd/paperless_figure_assets"
CONFIG_FILE = "/home/node/clawd/paperless_ingest_config.json"

DEFAULT_PAPERLESS_URL = "http://paperless:8000"
DEFAULT_PAPERLESS_TOKEN = "a451ceb5c13ac270faf3936405d207e4093ff580"

OLLAMA_URL = "http://ollama:11434/api/generate"
INFINITY_URL = os.getenv("INFINITY_URL", "http://infinity:7997/embeddings")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
DOCLING_URL = os.getenv("DOCLING_URL", "http://docling:5001")
COLLECTION = "universal_knowledge"

VLM_MODEL = "minicpm-v:latest"
EMBED_MODEL = "mixedbread-ai/mxbai-embed-large-v1"
EMBED_DIM = 1024

IMAGE_PAGE_THRESHOLD = 100
CHUNK_SIZE = 800
MAX_PAGES = 60
IDLE_SLEEP = 120
CAPTION_TOKENS = ("fig", "figure", "table", "chart", "graph", "図", "表", "グラフ")


def load_paperless_config() -> tuple[str, str]:
    url = os.getenv("PAPERLESS_URL", DEFAULT_PAPERLESS_URL).strip()
    token = os.getenv("PAPERLESS_TOKEN", DEFAULT_PAPERLESS_TOKEN).strip()
    try:
        payload = json.loads(Path(CONFIG_FILE).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            url = str(payload.get("paperlessUrl") or url).strip()
            token = str(payload.get("paperlessToken") or token).strip()
    except Exception:
        pass
    return url, token


PAPERLESS_URL, PAPERLESS_TOKEN = load_paperless_config()


def paperless_headers() -> dict[str, str]:
    return {"Authorization": f"Token {PAPERLESS_TOKEN}"}


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    if sys.stdout.isatty():
        print(line, flush=True)
        return
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {"processed": {}}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def candidate_urls(primary: str, fallbacks: Iterable[str]) -> list[str]:
    urls: list[str] = []
    for item in [primary, *fallbacks]:
        value = (item or "").strip()
        if value and value not in urls:
            urls.append(value)
    return urls


def qdrant_candidates() -> list[str]:
    return candidate_urls(
        QDRANT_URL,
        [
            "http://qdrant:6333",
            "http://host.docker.internal:6333",
            "http://127.0.0.1:6333",
        ],
    )


def infinity_embeddings_url() -> str:
    base = INFINITY_URL.rstrip("/")
    if base.endswith("/embeddings"):
        return base
    return f"{base}/embeddings"


def write_status(**kwargs) -> None:
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"),
        "service": "paperless_ingest_watchdog",
        "paperlessUrl": PAPERLESS_URL,
        "collection": COLLECTION,
        "qdrantCandidates": qdrant_candidates(),
    }
    payload.update(kwargs)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def looks_like_weak_caption(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return True
    if len(value) <= 3:
        return True
    digit_count = sum(1 for ch in value if ch.isdigit())
    alpha_count = sum(1 for ch in value if ch.isalpha())
    cjk_count = sum(1 for ch in value if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff")
    punctuation_count = sum(1 for ch in value if not ch.isalnum() and not ch.isspace())
    meaningful = digit_count + alpha_count + cjk_count
    if meaningful == 0:
        return True
    if punctuation_count > meaningful:
        return True
    return False


def ensure_figure_asset_dir() -> None:
    os.makedirs(FIGURE_ASSET_DIR, exist_ok=True)


def save_page_asset(doc_id: int, page_no: int, png_bytes: bytes) -> str | None:
    if not png_bytes:
        return None
    ensure_figure_asset_dir()
    asset_name = f"paperless_{doc_id}_page_{page_no:04d}.png"
    asset_path = os.path.join(FIGURE_ASSET_DIR, asset_name)
    try:
        with open(asset_path, "wb") as fh:
            fh.write(png_bytes)
        return asset_path
    except Exception as exc:
        log(f"  Figure asset save failed (doc={doc_id}, page={page_no}): {exc}", "WARN")
        return None


def fetch_all_docs(state: dict) -> list[dict]:
    processed = state.get("processed", {})
    new_docs = []
    url = f"{PAPERLESS_URL}/api/documents/?page_size=100&ordering=id"
    while url:
        try:
            resp = requests.get(url, headers=paperless_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log(f"Paperless list error: {exc}", "ERROR")
            break
        for doc in data.get("results", []):
            doc_id = str(doc["id"])
            if doc_id not in processed:
                new_docs.append(
                    {
                        "id": doc["id"],
                        "title": doc.get("title", ""),
                        "created": doc.get("created", ""),
                        "added": doc.get("added", ""),
                        "page_count": doc.get("page_count", 0),
                    }
                )
        url = data.get("next")
    return new_docs


def fetch_doc_detail(doc_id: int) -> dict | None:
    try:
        resp = requests.get(f"{PAPERLESS_URL}/api/documents/{doc_id}/", headers=paperless_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        log(f"  Paperless detail error (id={doc_id}): {exc}", "WARN")
        return None


def download_pdf(doc_id: int) -> bytes | None:
    try:
        resp = requests.get(f"{PAPERLESS_URL}/api/documents/{doc_id}/download/", headers=paperless_headers(), timeout=60)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        log(f"  Paperless download error (id={doc_id}): {exc}", "WARN")
        return None


def extract_text_docling(doc_id: int) -> str | None:
    pdf_url = f"{PAPERLESS_URL}/api/documents/{doc_id}/download/"
    try:
        resp = requests.post(
            f"{DOCLING_URL}/v1/convert/source",
            json={
                "sources": [
                    {
                        "kind": "http",
                        "url": pdf_url,
                        "headers": paperless_headers(),
                    }
                ],
                "options": {
                    "to_formats": ["md"],
                    "do_ocr": True,
                    "force_ocr": False,
                    "include_images": False,
                },
            },
            timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()
        for item in result.get("output", []):
            markdown = item.get("markdown", "").strip()
            if markdown:
                return markdown
        document = result.get("document", {})
        for item in document.get("export_results", []):
            if item.get("format") == "md":
                content = item.get("content", "").strip()
                if content:
                    return content
        return None
    except Exception as exc:
        log(f"  Docling failed (id={doc_id}): {exc}", "WARN")
        return None


def extract_pdf_pages(pdf_bytes: bytes, max_pages: int = MAX_PAGES) -> list[dict]:
    try:
        import fitz
    except ImportError:
        log("PyMuPDF not installed - cannot extract PDF pages", "ERROR")
        return []

    pages: list[dict] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total = len(doc)
        limit = min(total, max_pages) if max_pages else total
        for i in range(limit):
            page = doc[i]
            text = page.get_text("text").strip()
            blocks = page.get_text("blocks") or []
            image_count = len(page.get_images(full=True))
            png_bytes = None
            if len(text) < IMAGE_PAGE_THRESHOLD:
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                png_bytes = pix.tobytes("png")
            short_lines = []
            caption_lines = []
            structured_lines = []
            numeric_heavy_lines = 0
            for block in blocks:
                block_text = (block[4] or "").strip()
                if not block_text:
                    continue
                y0 = float(block[1]) if len(block) > 1 else 0.0
                for raw_line in block_text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    structured_lines.append({"text": line, "y": y0})
                    if len(line) <= 120:
                        short_lines.append(line)
                    lowered = line.lower()
                    if any(token in lowered for token in CAPTION_TOKENS):
                        caption_lines.append(line)
                    digit_count = sum(1 for ch in line if ch.isdigit())
                    delimiter_hits = line.count("|") + line.count("\t") + line.count("%")
                    if digit_count >= 5 or (digit_count >= 3 and delimiter_hits >= 1):
                        numeric_heavy_lines += 1
            caption_candidates = [
                line
                for line in short_lines
                if any(token in line.lower() for token in ["fig", "figure", "table", "図", "表", "グラフ", "chart"])
            ]
            nearby_caption = caption_candidates[0] if caption_candidates else (short_lines[0] if short_lines else "")
            if caption_lines:
                caption_candidates = caption_lines[:]
                nearby_caption = caption_candidates[0]
            elif structured_lines:
                sorted_lines = sorted(structured_lines, key=lambda item: item["y"])
                top_candidates = [item["text"] for item in sorted_lines[:3] if len(item["text"]) <= 120]
                bottom_candidates = [item["text"] for item in sorted_lines[-3:] if len(item["text"]) <= 120]
                fallback_candidates = bottom_candidates + top_candidates
                if fallback_candidates:
                    nearby_caption = fallback_candidates[0]
            if looks_like_weak_caption(nearby_caption):
                nearby_caption = ""
            table_like = numeric_heavy_lines >= 4
            table_score = numeric_heavy_lines
            if image_count == 0 and len(text) >= IMAGE_PAGE_THRESHOLD:
                table_score += 1
            if any(
                any(ch.isdigit() for ch in line) and any(token in line for token in ("|", "%", "mm", "kg", "℃"))
                for line in short_lines
            ):
                table_score += 1
            table_like = table_score >= 4
            caption_confidence = "high" if caption_lines else ("medium" if nearby_caption else "low")
            if len(text) > 30:
                page_type = "text_like"
            elif image_count > 0:
                page_type = "image_only"
            else:
                page_type = "unknown"
            pages.append(
                {
                    "index": i,
                    "total": total,
                    "text": text,
                    "png": png_bytes,
                    "text_len": len(text),
                    "image_count": image_count,
                    "page_type": page_type,
                    "nearby_caption": nearby_caption,
                    "caption_confidence": caption_confidence,
                    "table_like": table_like,
                    "table_score": table_score,
                    "numeric_heavy_lines": numeric_heavy_lines,
                }
            )
        doc.close()
    except Exception as exc:
        log(f"  PDF extract error: {exc}", "WARN")
    return pages


def detect_pdf_type_from_pages(pages: list[dict]) -> str:
    if not pages:
        return "unknown"
    text_like_pages = sum(1 for page in pages if page.get("page_type") == "text_like")
    image_only_pages = sum(1 for page in pages if page.get("page_type") == "image_only")
    total_pages = len(pages)
    if text_like_pages == total_pages:
        return "born_digital"
    if image_only_pages == total_pages:
        return "scanned"
    if text_like_pages > 0 and image_only_pages > 0:
        return "hybrid"
    return "unknown"


def analyze_page_with_vlm(png_bytes: bytes, page_idx: int, total_pages: int, doc_title: str) -> str:
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    prompt = (
        f"You are analyzing page {page_idx + 1} of {total_pages} from a technical document: '{doc_title}'.\n"
        "Extract all useful information on this page.\n"
        "Include text, tables, labels, diagram structure, formulas, callouts, and captions.\n"
        "Do not summarize loosely. Keep the output faithful to the page."
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
    except Exception as exc:
        log(f"  VLM error page {page_idx + 1}: {exc}", "WARN")
        return ""


def embed_text(text: str) -> list[float] | None:
    try:
        resp = requests.post(
            infinity_embeddings_url(),
            json={"model": EMBED_MODEL, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as exc:
        log(f"  Embed error: {exc}", "WARN")
        return None


def upsert_to_qdrant(point_id: int, vector: list[float], payload_data: dict) -> bool:
    errors: list[str] = []
    for base_url in qdrant_candidates():
        try:
            resp = requests.put(
                f"{base_url}/collections/{COLLECTION}/points",
                json={"points": [{"id": point_id, "vector": vector, "payload": payload_data}]},
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            errors.append(f"{base_url}: {exc}")
    log(f"  Qdrant upsert error: {' | '.join(errors)}", "WARN")
    return False


def make_point_id(doc_id: int, page_idx: int, chunk_idx: int) -> int:
    raw = f"paperless::{doc_id}::p{page_idx}::c{chunk_idx}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:15], 16)


def build_base_payload(
    doc_id: int,
    doc_title: str,
    tags: list[str],
    created: str,
    pdf_type: str,
    total_pages: int,
    source_method: str,
) -> dict:
    return {
        "source": f"paperless/{doc_id}/{doc_title}",
        "paperless_id": doc_id,
        "title": doc_title,
        "tags": tags,
        "created": created,
        "ingested_at": datetime.now().isoformat(),
        "pdf_type": pdf_type,
        "total_pages": total_pages,
        "source_method": source_method,
    }


def upsert_chunks(
    doc_id: int,
    page_idx: int,
    chunks: list[str],
    base_payload: dict,
    item_type: str,
    group_id: str,
    page_meta: dict | None = None,
) -> int:
    ingested = 0
    page_meta = page_meta or {}
    for chunk_idx, chunk in enumerate(chunks):
        vector = embed_text(chunk)
        if not vector or len(vector) != EMBED_DIM:
            continue
        point_id = make_point_id(doc_id, page_idx, chunk_idx)
        payload = dict(base_payload)
        payload.update(
            {
                "page": page_idx + 1,
                "chunk": chunk_idx,
                "content": chunk,
                "item_type": item_type,
                "group_id": group_id,
            }
        )
        payload.update(page_meta)
        if upsert_to_qdrant(point_id, vector, payload):
            ingested += 1
    return ingested


def ingest_raw_text(
    text: str,
    doc_id: int,
    doc_title: str,
    tags: list[str],
    created: str,
    *,
    pdf_type: str,
    total_pages: int,
    source_method: str,
    item_type: str,
    group_id: str,
) -> int:
    base_payload = build_base_payload(
        doc_id,
        doc_title,
        tags,
        created,
        pdf_type=pdf_type,
        total_pages=total_pages,
        source_method=source_method,
    )
    return upsert_chunks(
        doc_id,
        0,
        chunk_text(text),
        base_payload,
        item_type=item_type,
        group_id=group_id,
        page_meta={
            "page_type": item_type,
            "page_text_len": len(text),
            "page_image_count": None,
        },
    )


def process_document(doc_meta: dict, state: dict) -> None:
    doc_id = doc_meta["id"]
    doc_title = doc_meta["title"] or f"doc_{doc_id}"
    log(f"Processing doc {doc_id}: {doc_title!r}")
    write_status(stage="processing", paperlessId=doc_id, title=doc_title, processedCount=len(state.get("processed", {})))

    detail = fetch_doc_detail(doc_id)
    if not detail:
        state["processed"][str(doc_id)] = {"title": doc_title, "error": "fetch_detail_failed", "ts": datetime.now().isoformat()}
        save_state(state)
        return

    ocr_content = (detail.get("content") or "").strip()
    raw_tags = detail.get("tags", [])
    tags = [str(t) if isinstance(t, int) else t.get("name", str(t)) for t in raw_tags]
    created = detail.get("created", "")
    total_pages = detail.get("page_count") or doc_meta.get("page_count") or 1

    docling_text = extract_text_docling(doc_id)
    if docling_text and len(docling_text) > 200:
        log(f"  Docling OK ({len(docling_text)} chars) - skipping PyMuPDF/VLM")
        ingested = ingest_raw_text(
            docling_text,
            doc_id,
            doc_title,
            tags,
            created,
            pdf_type="docling_structured",
            total_pages=total_pages,
            source_method="docling_markdown",
            item_type="docling_markdown",
            group_id=f"doc_{doc_id}_docling",
        )
        state["processed"][str(doc_id)] = {
            "title": doc_title,
            "pages": 1,
            "chunks": ingested,
            "method": "docling",
            "pdf_type": "docling_structured",
            "ts": datetime.now().isoformat(),
        }
        save_state(state)
        return

    pdf_bytes = download_pdf(doc_id)
    if not pdf_bytes:
        if ocr_content:
            log(f"  PDF unavailable - falling back to full OCR text ({len(ocr_content)} chars)")
            ingested = ingest_raw_text(
                ocr_content,
                doc_id,
                doc_title,
                tags,
                created,
                pdf_type="pdf_unavailable",
                total_pages=total_pages,
                source_method="paperless_ocr_blob",
                item_type="ocr_blob",
                group_id=f"doc_{doc_id}_ocr_blob",
            )
            state["processed"][str(doc_id)] = {
                "title": doc_title,
                "pages": 1,
                "chunks": ingested,
                "pdf_type": "pdf_unavailable",
                "ts": datetime.now().isoformat(),
            }
        else:
            state["processed"][str(doc_id)] = {"title": doc_title, "error": "no_content", "ts": datetime.now().isoformat()}
        save_state(state)
        return

    pages = extract_pdf_pages(pdf_bytes, max_pages=MAX_PAGES)
    if not pages:
        if ocr_content:
            log(f"  PyMuPDF unavailable - using full OCR blob ({len(ocr_content)} chars)")
            ingested = ingest_raw_text(
                ocr_content,
                doc_id,
                doc_title,
                tags,
                created,
                pdf_type="unknown",
                total_pages=total_pages,
                source_method="paperless_ocr_blob",
                item_type="ocr_blob",
                group_id=f"doc_{doc_id}_ocr_blob",
            )
            state["processed"][str(doc_id)] = {
                "title": doc_title,
                "pages": 1,
                "chunks": ingested,
                "pdf_type": "unknown",
                "ts": datetime.now().isoformat(),
            }
        else:
            state["processed"][str(doc_id)] = {"title": doc_title, "error": "no_pages", "ts": datetime.now().isoformat()}
        save_state(state)
        return

    pdf_type = detect_pdf_type_from_pages(pages)
    ingested = 0
    for page in pages:
        idx = page["index"]
        page_text = page["text"]
        png_bytes = page["png"]
        asset_path = save_page_asset(doc_id, idx + 1, png_bytes) if png_bytes else None
        page_meta = {
            "page_type": page.get("page_type"),
            "page_text_len": page.get("text_len"),
            "page_image_count": page.get("image_count"),
            "nearby_caption": page.get("nearby_caption"),
            "caption_confidence": page.get("caption_confidence"),
            "table_like": page.get("table_like"),
            "table_score": page.get("table_score"),
            "numeric_heavy_lines": page.get("numeric_heavy_lines"),
            "source_asset_path": asset_path,
        }
        base_payload = build_base_payload(
            doc_id,
            doc_title,
            tags,
            created,
            pdf_type=pdf_type,
            total_pages=page["total"],
            source_method="pymupdf_native",
        )

        if len(page_text) >= IMAGE_PAGE_THRESHOLD:
            content = f"[Page {idx + 1}/{page['total']}]\n{page_text}"
            item_type = "text_page"
            source_method = "pymupdf_native"
            if page.get("table_like"):
                item_type = "table_rich_page"
        elif png_bytes:
            log(f"  Page {idx + 1}/{page['total']}: image-heavy -> VLM")
            vlm_out = analyze_page_with_vlm(png_bytes, idx, page["total"], doc_title)
            content = f"[Page {idx + 1}/{page['total']} - VLM]\n{vlm_out}" if vlm_out else ""
            item_type = "figure_rich_page"
            source_method = "vlm_page_extract"
            time.sleep(0.5)
        else:
            content = ""
            item_type = "unknown_page"
            source_method = "unknown"

        if not content.strip():
            continue

        if page.get("nearby_caption"):
            content = f"[Caption]\n{page['nearby_caption']}\n\n{content}"

        base_payload["source_method"] = source_method
        ingested += upsert_chunks(
            doc_id,
            idx,
            chunk_text(content),
            base_payload,
            item_type=item_type,
            group_id=f"doc_{doc_id}_page_{idx + 1}_{item_type}",
            page_meta=page_meta,
        )

    log(f"  doc {doc_id} ({doc_title!r}): {len(pages)} pages -> {ingested} chunks ({pdf_type})")
    state["processed"][str(doc_id)] = {
        "title": doc_title,
        "pages": len(pages),
        "chunks": ingested,
        "pdf_type": pdf_type,
        "ts": datetime.now().isoformat(),
    }
    save_state(state)


def acquire_pid_lock() -> bool:
    my_pid = os.getpid()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as fh:
                old_pid = int(fh.read().strip())
            os.kill(old_pid, 0)
            log(f"Another instance already running (PID {old_pid}). Exiting.", "WARNING")
            return False
        except (ProcessLookupError, ValueError, OSError):
            log("Stale PID file found. Overwriting.", "INFO")
    with open(PID_FILE, "w", encoding="utf-8") as fh:
        fh.write(str(my_pid))
    log(f"PID lock acquired (PID {my_pid})")
    return True


def release_pid_lock() -> None:
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as fh:
                stored = int(fh.read().strip())
            if stored == os.getpid():
                os.remove(PID_FILE)
    except Exception:
        pass


def main() -> None:
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
    write_status(stage="starting", processedCount=already, idleSleepSeconds=IDLE_SLEEP)

    consecutive_failures = 0
    while True:
        try:
            write_status(stage="polling", processedCount=len(state.get("processed", {})), idleSleepSeconds=IDLE_SLEEP)
            new_docs = fetch_all_docs(state)
            consecutive_failures = 0  # Reset on success
            if new_docs:
                log(f"Found {len(new_docs)} new document(s) to process")
                write_status(stage="processing_batch", queueLength=len(new_docs), processedCount=len(state.get("processed", {})))
                for doc_meta in new_docs:
                    try:
                        process_document(doc_meta, state)
                    except Exception as exc:
                        doc_id = doc_meta["id"]
                        log(f"  ERROR processing doc {doc_id}: {exc}", "ERROR")
                        log(traceback.format_exc(), "ERROR")
                        state["processed"][str(doc_id)] = {
                            "title": doc_meta.get("title", ""),
                            "error": str(exc),
                            "ts": datetime.now().isoformat(),
                        }
                        save_state(state)
                        write_status(
                            stage="error",
                            paperlessId=doc_id,
                            title=doc_meta.get("title", ""),
                            lastError=str(exc),
                            processedCount=len(state.get("processed", {})),
                        )
            else:
                log(f"No new documents. Sleeping {IDLE_SLEEP}s...")
                write_status(stage="idle", queueLength=0, processedCount=len(state.get("processed", {})), idleSleepSeconds=IDLE_SLEEP)
            time.sleep(IDLE_SLEEP)
        except Exception as exc:
            consecutive_failures += 1
            backoff = min(IDLE_SLEEP * (2 ** (consecutive_failures - 1)), 3600)
            log(f"Main loop error (failure {consecutive_failures}): {exc}", "ERROR")
            log(f"Backing off for {backoff}s...", "INFO")
            write_status(stage="error", lastError=str(exc), processedCount=len(state.get("processed", {})))
            time.sleep(backoff)


if __name__ == "__main__":
    if not acquire_pid_lock():
        sys.exit(1)
    atexit.register(release_pid_lock)
    signal.signal(signal.SIGTERM, lambda _s, _f: sys.exit(0))
    main()
