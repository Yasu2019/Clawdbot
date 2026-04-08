#!/usr/bin/env python3
"""
rag_queue_processor.py — RAGキュー → Qdrant universal_knowledge
=================================================================
/home/node/clawd/rag_queue/ を監視し、投入されたファイルを
テキスト抽出 → チャンク → Infinity埋め込み → Qdrant格納 する。

対応フォーマット:
  PDF   → Docling (優先) → PyMuPDF (フォールバック)
  Excel → openpyxl でセル内容をテキスト化
  CSV   → 直接読み込み
  Text/MD/JSON/YAML → 直接読み込み

Usage:
  python3 /home/node/clawd/rag_queue_processor.py
  python3 /home/node/clawd/rag_queue_processor.py --dry-run
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── 設定 ─────────────────────────────────────────────────────────────────────

JST        = timezone(timedelta(hours=9))
QUEUE_DIR  = Path("/home/node/clawd/rag_queue")
DONE_DIR   = QUEUE_DIR / "done"
ERROR_DIR  = QUEUE_DIR / "error"
LOG_FILE   = Path("/home/node/clawd/rag_queue_processor.log")
STATE_FILE = Path("/home/node/clawd/rag_queue_processor_state.json")

INFINITY_URL = os.getenv("INFINITY_URL", "http://infinity:7997")
QDRANT_URL   = os.getenv("QDRANT_URL",   "http://qdrant:6333")
DOCLING_URL  = os.getenv("DOCLING_URL",  "http://docling:5001")

COLLECTION  = "universal_knowledge"
EMBED_MODEL = "mixedbread-ai/mxbai-embed-large-v1"
EMBED_DIM   = 1024
CHUNK_SIZE  = 800
POLL_SEC    = 30   # キュー監視間隔

TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT_TOKEN", "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4")
TELEGRAM_CID = os.environ.get("TELEGRAM_CHAT_ID",   "8173025084")

DRY_RUN = "--dry-run" in sys.argv

# 対応拡張子
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".xml", ".log", ".csv"}
PDF_EXTENSIONS  = {".pdf"}
EXCEL_EXTENSIONS = {".xlsx", ".xls"}


# ── ユーティリティ ─────────────────────────────────────────────────────────────

def now() -> datetime:
    return datetime.now(JST)

def log(msg: str, level: str = "INFO") -> None:
    ts   = now().strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] [{level}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass

def send_telegram(text: str) -> None:
    if not TELEGRAM_BOT or not TELEGRAM_CID:
        return
    if DRY_RUN:
        log(f"[dry-run] Telegram: {text[:100]}")
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CID, "text": text, "parse_mode": "HTML"
    }).encode()
    try:
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram error: {e}", "WARN")

def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"processed": {}}

def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"State save error: {e}", "WARN")


# ── テキスト抽出 ───────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]


def extract_pdf_docling(filepath: Path) -> str | None:
    """Docling の /v1/convert/file エンドポイントで PDF → Markdown"""
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{DOCLING_URL}/v1/convert/file",
                files={"file": (filepath.name, f, "application/pdf")},
                data={"options": json.dumps({
                    "to_formats":     ["md"],
                    "do_ocr":         True,
                    "force_ocr":      False,
                    "include_images": False,
                })},
                timeout=300,
            )
        resp.raise_for_status()
        result = resp.json()
        for item in result.get("output", []):
            md = item.get("markdown", "").strip()
            if md:
                return md
        # v2 API レスポンス形式
        doc = result.get("document", {})
        for item in doc.get("export_results", []):
            if item.get("format") == "md":
                content = item.get("content", "").strip()
                if content:
                    return content
        return None
    except Exception as e:
        log(f"  Docling error: {e}", "WARN")
        return None


def extract_pdf_pymupdf(filepath: Path) -> str | None:
    """PyMuPDF (fitz) で PDF → テキスト"""
    try:
        import fitz
        doc  = fitz.open(str(filepath))
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.strip() or None
    except Exception as e:
        log(f"  PyMuPDF error: {e}", "WARN")
        return None


def extract_excel(filepath: Path) -> str | None:
    """openpyxl で Excel → テキスト"""
    try:
        import openpyxl
        wb    = openpyxl.load_workbook(str(filepath), read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            lines.append(f"=== シート: {ws.title} ===")
            for row in ws.iter_rows(values_only=True):
                vals = [str(v) for v in row if v is not None]
                if vals:
                    lines.append(" | ".join(vals))
        wb.close()
        return "\n".join(lines) or None
    except Exception as e:
        log(f"  Excel error: {e}", "WARN")
        return None


def extract_text(filepath: Path) -> tuple[str | None, str]:
    """
    ファイルからテキストを抽出する。
    Returns: (text, source_method)
    """
    ext = filepath.suffix.lower()

    if ext in PDF_EXTENSIONS:
        text = extract_pdf_docling(filepath)
        if text and len(text) > 100:
            log(f"  Docling extraction: {len(text)} chars")
            return text, "docling_markdown"
        text = extract_pdf_pymupdf(filepath)
        if text:
            log(f"  PyMuPDF extraction: {len(text)} chars")
            return text, "pymupdf_native"
        return None, "pdf_failed"

    if ext in EXCEL_EXTENSIONS:
        text = extract_excel(filepath)
        if text:
            log(f"  Excel extraction: {len(text)} chars")
            return text, "openpyxl"
        return None, "excel_failed"

    if ext in TEXT_EXTENSIONS:
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                text = f.read()
            log(f"  Text extraction: {len(text)} chars")
            return text, "direct_read"
        except Exception as e:
            log(f"  Text read error: {e}", "WARN")
            return None, "text_failed"

    return None, "unsupported_format"


# ── 埋め込み & Qdrant ────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float] | None:
    base = INFINITY_URL.rstrip("/")
    url  = f"{base}/embeddings" if not base.endswith("/embeddings") else base
    try:
        resp = requests.post(
            url,
            json={"model": EMBED_MODEL, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        vec = resp.json()["data"][0]["embedding"]
        if len(vec) != EMBED_DIM:
            log(f"  Embed dim mismatch: {len(vec)} != {EMBED_DIM}", "WARN")
            return None
        return vec
    except Exception as e:
        log(f"  Embed error: {e}", "WARN")
        return None


def upsert_to_qdrant(point_id: int, vector: list[float], payload: dict) -> bool:
    candidates = [QDRANT_URL, "http://qdrant:6333", "http://host.docker.internal:6333"]
    for base in candidates:
        try:
            resp = requests.put(
                f"{base}/collections/{COLLECTION}/points",
                json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except Exception:
            continue
    log("  Qdrant upsert failed on all candidates", "WARN")
    return False


def make_point_id(filename: str, chunk_idx: int) -> int:
    raw = f"rag_queue::{filename}::c{chunk_idx}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:15], 16)


# ── ファイル処理 ───────────────────────────────────────────────────────────────

def process_file(filepath: Path, state: dict) -> None:
    fname   = filepath.name
    size_kb = filepath.stat().st_size / 1024
    log(f"Processing: {fname} ({size_kb:.1f} KB)")

    # テキスト抽出
    text, method = extract_text(filepath)
    if not text or len(text.strip()) < 20:
        log(f"  No extractable text ({method}) — moving to error/", "WARN")
        ERROR_DIR.mkdir(parents=True, exist_ok=True)
        dest = ERROR_DIR / fname
        if not DRY_RUN:
            filepath.rename(dest)
        state["processed"][fname] = {
            "status": "error", "reason": f"no_text:{method}",
            "ts": now().isoformat()
        }
        save_state(state)
        send_telegram(
            f"<b>⚠️ [RAG Queue] テキスト抽出失敗</b>\n"
            f"📄 <code>{fname}</code>\n方法: {method}"
        )
        return

    # チャンク分割 → 埋め込み → Qdrant
    chunks   = chunk_text(text)
    ingested = 0
    skipped  = 0

    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        if DRY_RUN:
            ingested += 1
            continue

        vector = embed_text(chunk)
        if not vector:
            skipped += 1
            continue

        point_id = make_point_id(fname, i)
        payload  = {
            "source":        f"rag_queue/{fname}",
            "filename":      fname,
            "title":         filepath.stem,
            "chunk":         i,
            "total_chunks":  len(chunks),
            "content":       chunk,
            "source_method": method,
            "file_size_kb":  round(size_kb, 1),
            "ingested_at":   now().isoformat(),
            "item_type":     "rag_queue_file",
        }
        if upsert_to_qdrant(point_id, vector, payload):
            ingested += 1
        else:
            skipped += 1

    log(f"  {fname}: {len(chunks)} chunks → {ingested} ingested, {skipped} skipped ({method})")

    # 処理済みフォルダへ移動
    if not DRY_RUN:
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        dest = DONE_DIR / fname
        if dest.exists():
            dest = DONE_DIR / f"{filepath.stem}_{int(time.time())}{filepath.suffix}"
        filepath.rename(dest)

    state["processed"][fname] = {
        "status":   "done",
        "chunks":   ingested,
        "method":   method,
        "ts":       now().isoformat(),
    }
    save_state(state)

    send_telegram(
        f"<b>🧠 [RAG Queue] インジェスト完了</b>\n"
        f"📄 <code>{fname}</code>  ({size_kb:.1f} KB)\n"
        f"チャンク: {ingested}/{len(chunks)}  方法: {method}\n"
        f"→ Qdrant <code>{COLLECTION}</code> に格納済み"
        + (" (dry-run)" if DRY_RUN else "")
    )


# ── メインループ ───────────────────────────────────────────────────────────────

def main() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("RAG Queue Processor started" + (" [DRY-RUN]" if DRY_RUN else ""))
    log(f"Queue   : {QUEUE_DIR}")
    log(f"Qdrant  : {QDRANT_URL}  collection={COLLECTION}")
    log(f"Infinity: {INFINITY_URL}  model={EMBED_MODEL}")
    log(f"Docling : {DOCLING_URL}")
    log(f"Poll    : {POLL_SEC}s")
    log("=" * 60)

    send_telegram(
        "<b>🧠 [RAG Queue Processor] 起動</b>\n"
        "rag_queue/ に投入したファイルを自動でQdrantに格納します\n"
        f"コレクション: <code>{COLLECTION}</code>"
        + (" (dry-run)" if DRY_RUN else "")
    )

    state = load_state()
    log(f"State: {len(state.get('processed', {}))} file(s) already processed")

    # 対応拡張子セット
    supported = PDF_EXTENSIONS | EXCEL_EXTENSIONS | TEXT_EXTENSIONS

    while True:
        try:
            new_files = [
                f for f in QUEUE_DIR.iterdir()
                if f.is_file()
                and not f.name.startswith(".")
                and f.suffix.lower() in supported
                and f.name not in state.get("processed", {})
            ]

            if new_files:
                log(f"Found {len(new_files)} new file(s) in queue")
                for filepath in sorted(new_files, key=lambda f: f.stat().st_mtime):
                    try:
                        # ファイル書き込み完了待ち
                        size1 = filepath.stat().st_size
                        time.sleep(1)
                        if not filepath.exists():
                            continue
                        if filepath.stat().st_size != size1:
                            log(f"  {filepath.name}: still writing, skipping")
                            continue
                        process_file(filepath, state)
                    except Exception as e:
                        log(f"  Error: {filepath.name}: {e}", "ERROR")
            else:
                log(f"Queue empty. Next check in {POLL_SEC}s...")

        except Exception as e:
            log(f"Main loop error: {e}", "ERROR")

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
