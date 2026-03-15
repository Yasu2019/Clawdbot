#!/usr/bin/env python3
"""
ingest_eml_v2.py  — Phase 1 + Phase 2
========================================
Phase 1: .eml 本文 → Infinity embed → Qdrant universal_knowledge
Phase 2: .eml 添付ファイル → Docling/openpyxl/python-docx → Infinity embed → Qdrant universal_knowledge

ソース: /home/node/clawd/paperless_consume/email/**/*.eml
状態:   /home/node/clawd/ingest_eml_state.json  (v1 と共通、attachment キーを追加)

実行:
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/ingest_eml_v2.py
"""

import io
import os
import sys
import json
import hashlib
import requests
import traceback
from pathlib import Path
from datetime import datetime
from email import message_from_bytes, message_from_string
from email.header import decode_header

# ── Configuration ────────────────────────────────────────────────────────────────
EMAIL_ROOT   = "/home/node/clawd/paperless_consume/email"
STATE_FILE   = "/home/node/clawd/ingest_eml_state.json"
LOG_FILE     = "/home/node/clawd/ingest_eml.log"

INFINITY_URL = "http://infinity:7997/embeddings"
QDRANT_URL   = "http://qdrant:6333"
COLLECTION   = "universal_knowledge"
EMBED_MODEL  = "mixedbread-ai/mxbai-embed-large-v1"
EMBED_DIM    = 1024

DOCLING_URL  = "http://docling:5001"

CHUNK_SIZE    = 600
MAX_CHUNKS    = 20   # cap per email (12,000 chars = ~8,000 tokens)
EMBED_BATCH   = 8    # flush buffer every N chunks
QDRANT_BATCH  = 32
LOG_INTERVAL  = 100

# 添付ファイル処理対象の拡張子
DOCLING_EXTS  = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
EXCEL_EXTS    = {".xlsx", ".xls", ".xlsm"}
PLAIN_EXTS    = {".txt", ".csv", ".tsv"}
SKIP_EXTS     = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".dat", ".dxf",
                 ".step", ".vcf", ".stp", ".stl", ".json", ".xml"}

# ── Logging ──────────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    if sys.stdout.isatty():
        print(line, flush=True)
    else:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

# ── State ─────────────────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": {}, "attachments": {}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ── Email parsing ────────────────────────────────────────────────────────────────
def decode_mime_words(s):
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for raw, enc in parts:
        if isinstance(raw, bytes):
            for charset in [enc or "utf-8", "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                try:
                    decoded.append(raw.decode(charset))
                    break
                except Exception:
                    continue
            else:
                decoded.append(raw.decode("utf-8", errors="replace"))
        else:
            decoded.append(str(raw))
    return "".join(decoded)

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct   = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    for enc in [charset, "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                        try:
                            body += payload.decode(enc)
                            break
                        except Exception:
                            continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            for enc in [charset, "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                try:
                    body = payload.decode(enc)
                    break
                except Exception:
                    continue
    return body.strip()

def extract_attachments(msg):
    """Returns list of {filename, data, ext} for processable attachments."""
    result = []
    if not msg.is_multipart():
        return result
    for part in msg.walk():
        disp = str(part.get("Content-Disposition", ""))
        fn   = part.get_filename()
        if not fn:
            continue
        fn  = decode_mime_words(fn).strip()
        ext = Path(fn).suffix.lower()
        if ext in SKIP_EXTS:
            continue
        if ext not in (DOCLING_EXTS | EXCEL_EXTS | PLAIN_EXTS):
            continue
        data = part.get_payload(decode=True)
        if data and len(data) > 0:
            result.append({"filename": fn, "data": data, "ext": ext})
    return result

def parse_eml(filepath):
    try:
        rel   = Path(filepath).relative_to(EMAIL_ROOT)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "その他"
        person   = parts[1] if len(parts) > 2 else ""

        raw = Path(filepath).read_bytes()
        msg = None
        for enc in ["utf-8", "iso-2022-jp", "cp932", "latin-1"]:
            try:
                msg = message_from_string(raw.decode(enc))
                break
            except Exception:
                continue
        if msg is None:
            msg = message_from_bytes(raw)

        subject     = decode_mime_words(msg.get("subject", ""))
        from_       = decode_mime_words(msg.get("from", ""))
        to_         = decode_mime_words(msg.get("to", ""))
        date_       = msg.get("date", "")
        body        = extract_body(msg)
        attachments = extract_attachments(msg)

        return {
            "filepath":    filepath,
            "category":    category,
            "person":      person,
            "subject":     subject,
            "from":        from_,
            "to":          to_,
            "date":        date_,
            "body":        body,
            "attachments": attachments,
        }
    except Exception as e:
        log(f"  Parse error {Path(filepath).name}: {e}", "WARN")
        return None

# ── Chunking ─────────────────────────────────────────────────────────────────────
def make_chunks(meta):
    subject   = meta["subject"]
    full_text = f"件名: {subject}\n差出人: {meta['from']}\n日付: {meta['date']}\n\n{meta['body']}".strip()
    if len(full_text) < 20:
        return []

    rel_path     = str(Path(meta["filepath"]).relative_to(EMAIL_ROOT))
    base_payload = {
        "source":   f"email/{rel_path}",
        "category": meta["category"],
        "person":   meta["person"],
        "subject":  meta["subject"],
        "from":     meta["from"],
        "to":       meta["to"],
        "date":     meta["date"],
    }
    result = []
    for ci, start in enumerate(range(0, len(full_text), CHUNK_SIZE)):
        if ci >= MAX_CHUNKS:
            break
        chunk = full_text[start:start + CHUNK_SIZE]
        if not chunk.strip():
            continue
        pid = int(hashlib.md5(f"email::{meta['filepath']}::c{ci}".encode()).hexdigest()[:15], 16)
        result.append((chunk, {**base_payload, "chunk": ci, "content": chunk}, pid))
    return result

def make_attachment_chunks(meta, filename, text):
    if len(text.strip()) < 20:
        return []

    rel_path     = str(Path(meta["filepath"]).relative_to(EMAIL_ROOT))
    base_payload = {
        "source":          f"email_attachment/{rel_path}/{filename}",
        "category":        meta["category"],
        "person":          meta["person"],
        "subject":         meta["subject"],
        "from":            meta["from"],
        "date":            meta["date"],
        "attachment_name": filename,
    }
    result = []
    full_text = f"件名: {meta['subject']}  添付: {filename}\n\n{text}".strip()
    for ci, start in enumerate(range(0, len(full_text), CHUNK_SIZE)):
        chunk = full_text[start:start + CHUNK_SIZE]
        if not chunk.strip():
            continue
        key = f"email_att::{meta['filepath']}::{filename}::c{ci}"
        pid = int(hashlib.md5(key.encode()).hexdigest()[:15], 16)
        result.append((chunk, {**base_payload, "chunk": ci, "content": chunk}, pid))
    return result

# ── Attachment text extraction ────────────────────────────────────────────────────
def extract_via_docling(filename, data):
    """PDF / DOCX / DOC / PPTX → text via Docling /v1/convert/file"""
    try:
        resp = requests.post(
            f"{DOCLING_URL}/v1/convert/file",
            files={"files": (filename, io.BytesIO(data))},
            data={"to_formats": "md"},
            timeout=120,
        )
        resp.raise_for_status()
        d = resp.json()
        # Response structure: {"document": {"md_content": "..."}} or {"documents": [...]}
        md = ""
        doc = d.get("document", {})
        if isinstance(doc, dict):
            md = doc.get("md_content", "") or doc.get("markdown", "") or doc.get("text", "")
        if not md:
            for item in d.get("documents", []):
                if isinstance(item, dict):
                    md += item.get("md_content", "") or item.get("markdown", "")
        return md.strip()
    except Exception as e:
        log(f"  Docling error [{filename}]: {e}", "WARN")
        return ""

def extract_via_excel(filename, data):
    """XLSX / XLS / XLSM → text via openpyxl / xlrd"""
    ext = Path(filename).suffix.lower()
    try:
        if ext in {".xlsx", ".xlsm"}:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"[Sheet: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True, max_row=200):
                    cells = [str(c) if c is not None else "" for c in row]
                    line  = "\t".join(cells).strip()
                    if line.replace("\t", ""):
                        lines.append(line)
            return "\n".join(lines)
        elif ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(file_contents=data)
            lines = []
            for sheet in wb.sheets():
                lines.append(f"[Sheet: {sheet.name}]")
                for rx in range(min(sheet.nrows, 200)):
                    cells = [str(sheet.cell_value(rx, cx)) for cx in range(sheet.ncols)]
                    line  = "\t".join(cells).strip()
                    if line.replace("\t", ""):
                        lines.append(line)
            return "\n".join(lines)
    except Exception as e:
        log(f"  Excel error [{filename}]: {e}", "WARN")
    return ""

def extract_attachment_text(att):
    """Dispatch to appropriate extractor based on file extension."""
    ext = att["ext"]
    if ext in DOCLING_EXTS:
        return extract_via_docling(att["filename"], att["data"])
    elif ext in EXCEL_EXTS:
        return extract_via_excel(att["filename"], att["data"])
    elif ext in PLAIN_EXTS:
        for enc in ["utf-8", "cp932", "latin-1"]:
            try:
                return att["data"].decode(enc)
            except Exception:
                continue
    return ""

# ── Infinity batch embed ─────────────────────────────────────────────────────────
def batch_embed(texts):
    try:
        resp = requests.post(
            INFINITY_URL,
            json={"model": EMBED_MODEL, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [d["embedding"] for d in data]
    except Exception as e:
        log(f"  Embed batch error (n={len(texts)}): {e} — 1件リトライ", "WARN")
        results = []
        for t in texts:
            try:
                r = requests.post(INFINITY_URL, json={"model": EMBED_MODEL, "input": t}, timeout=30)
                r.raise_for_status()
                results.append(r.json()["data"][0]["embedding"])
            except Exception as e2:
                log(f"  Embed single error: {e2}", "WARN")
                results.append(None)
        return results

# ── Qdrant batch upsert ──────────────────────────────────────────────────────────
def batch_upsert(points):
    try:
        resp = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": points},
            timeout=30,
        )
        resp.raise_for_status()
        return len(points)
    except Exception as e:
        log(f"  Qdrant batch error: {e}", "WARN")
        return 0

# ── Flush helper ─────────────────────────────────────────────────────────────────
def flush_buffer(chunk_buf, ok_counter, file_chunks):
    if not chunk_buf:
        return
    texts  = [c[0] for c in chunk_buf]
    vecs   = batch_embed(texts)
    points = []
    for (text, payload, pid, fp), vec in zip(chunk_buf, vecs):
        if vec and len(vec) == EMBED_DIM:
            points.append({"id": pid, "vector": vec, "payload": {
                **payload, "ingested_at": datetime.now().isoformat()
            }})
            file_chunks[fp] = file_chunks.get(fp, 0) + 1
    if points:
        for i in range(0, len(points), QDRANT_BATCH):
            batch_upsert(points[i:i + QDRANT_BATCH])
        ok_counter[0] += len(set(c[3] for c in chunk_buf))
    chunk_buf.clear()

# ── Phase 1: email body ingest ───────────────────────────────────────────────────
def run_phase1(state):
    processed = state.setdefault("processed", {})
    all_emls  = sorted(Path(EMAIL_ROOT).rglob("*.eml"))
    pending   = [p for p in all_emls if str(p) not in processed]

    log(f"[Phase1] 総EML: {len(all_emls)}  未処理: {len(pending)}")
    if not pending:
        log("[Phase1] ✅ 新規ファイルなし。スキップ。")
        return 0

    ok          = [0]
    skip = err  = 0
    chunk_buf   = []
    file_chunks = {}

    for i, path in enumerate(pending):
        try:
            meta = parse_eml(str(path))
            if not meta:
                processed[str(path)] = {"chunks": 0, "error": "parse_failed", "ts": datetime.now().isoformat()}
                skip += 1
                continue

            chunks = make_chunks(meta)
            if not chunks:
                processed[str(path)] = {"chunks": 0, "ts": datetime.now().isoformat()}
                skip += 1
                continue

            for (ct, payload, pid) in chunks:
                chunk_buf.append((ct, payload, pid, str(path)))
                if len(chunk_buf) >= EMBED_BATCH:
                    flush_buffer(chunk_buf, ok, file_chunks)

            processed[str(path)] = {"subject": meta["subject"][:80], "ts": datetime.now().isoformat()}

        except Exception as e:
            log(f"  [{i+1}] ERROR {Path(str(path)).name}: {e}", "ERROR")
            processed[str(path)] = {"error": str(e), "ts": datetime.now().isoformat()}
            err += 1

        if (i + 1) % LOG_INTERVAL == 0:
            flush_buffer(chunk_buf, ok, file_chunks)
            state["processed"] = processed
            save_state(state)
            pct = (i + 1) / len(pending) * 100
            log(f"[Phase1] [{i+1}/{len(pending)}] {pct:.1f}%  ok={ok[0]}  skip={skip}  err={err}")

    flush_buffer(chunk_buf, ok, file_chunks)
    state["processed"] = processed
    save_state(state)
    log(f"[Phase1] ✅ 完了: ok={ok[0]}  skip={skip}  err={err}")
    return ok[0]

# ── Phase 2: attachment ingest ───────────────────────────────────────────────────
def run_phase2(state):
    processed   = state.get("processed", {})
    att_state   = state.setdefault("attachments", {})

    # Process EML files that have been body-processed and have attachments
    all_emls = sorted(Path(EMAIL_ROOT).rglob("*.eml"))
    ok   = [0]
    skip = err = 0
    chunk_buf   = []
    file_chunks = {}

    for i, path in enumerate(all_emls):
        fp = str(path)
        # Only process files already body-ingested (Phase 1)
        if fp not in processed:
            continue

        try:
            meta = parse_eml(fp)
            if not meta or not meta["attachments"]:
                continue

            for att in meta["attachments"]:
                att_key = f"{fp}::{att['filename']}"
                if att_key in att_state:
                    continue  # already processed

                text = extract_attachment_text(att)
                if not text or len(text.strip()) < 30:
                    att_state[att_key] = {"chunks": 0, "ts": datetime.now().isoformat()}
                    continue

                chunks = make_attachment_chunks(meta, att["filename"], text)
                for (ct, payload, pid) in chunks:
                    chunk_buf.append((ct, payload, pid, att_key))
                    if len(chunk_buf) >= EMBED_BATCH:
                        flush_buffer(chunk_buf, ok, file_chunks)

                att_state[att_key] = {
                    "filename": att["filename"],
                    "chunks":   len(chunks),
                    "ts":       datetime.now().isoformat(),
                }
                log(f"  [att] {att['filename']} ({len(chunks)} chunks)")

        except Exception as e:
            log(f"  [att] ERROR {path.name}: {e}", "ERROR")
            err += 1

        if (i + 1) % (LOG_INTERVAL * 5) == 0:
            flush_buffer(chunk_buf, ok, file_chunks)
            state["attachments"] = att_state
            save_state(state)
            log(f"[Phase2] [{i+1}/{len(all_emls)}] att_ok={ok[0]}  err={err}")

    flush_buffer(chunk_buf, ok, file_chunks)
    state["attachments"] = att_state
    save_state(state)
    log(f"[Phase2] ✅ 完了: ok={ok[0]}  skip={skip}  err={err}")
    return ok[0]

# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("  ingest_eml_v2.py (Phase1: body + Phase2: attachments)")
    log(f"  Source: {EMAIL_ROOT}")
    log("=" * 60)

    state = load_state()

    # Phase 1: email body → Qdrant
    n1 = run_phase1(state)

    # Phase 2: attachments → Docling/Excel → Qdrant
    # Check Docling availability first
    try:
        r = requests.get(f"{DOCLING_URL}/health", timeout=5)
        docling_ok = r.status_code == 200
    except Exception:
        docling_ok = False

    if docling_ok:
        log("[Phase2] Docling available — processing attachments")
        n2 = run_phase2(state)
    else:
        log("[Phase2] Docling unavailable — skipping attachment processing", "WARN")
        n2 = 0

    log(f"  Total indexed: Phase1={n1}  Phase2={n2}")

if __name__ == "__main__":
    main()
