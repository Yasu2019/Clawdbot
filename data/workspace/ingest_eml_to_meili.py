#!/usr/bin/env python3
"""
ingest_eml_to_meili.py  — Phase 3
=====================================
.eml ファイルをMeilisearchにインデックス（キーワード全文検索用）

インデックス構造:
  id, subject, from, to, date, category, person, body, filepath, attachment_names

実行:
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/ingest_eml_to_meili.py
"""

import os
import sys
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from email import message_from_bytes, message_from_string
from email.header import decode_header

# ── Configuration ────────────────────────────────────────────────────────────────
EMAIL_ROOT  = "/home/node/clawd/paperless_consume/email"
STATE_FILE  = "/home/node/clawd/ingest_eml_state.json"
MEILI_STATE = "/home/node/clawd/ingest_meili_state.json"
LOG_FILE    = "/home/node/clawd/ingest_eml.log"

MEILI_URL   = os.getenv("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY   = os.getenv("MEILI_KEY", "clawstack-meili-2026")
INDEX_NAME  = "emails"

BATCH_SIZE  = 100
LOG_INTERVAL = 500

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
def load_meili_state():
    if os.path.exists(MEILI_STATE):
        try:
            with open(MEILI_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"indexed": {}}

def save_meili_state(state):
    with open(MEILI_STATE, "w", encoding="utf-8") as f:
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

def extract_body_text(msg):
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

def get_attachment_names(msg):
    names = []
    if msg.is_multipart():
        for part in msg.walk():
            fn = part.get_filename()
            if fn:
                names.append(decode_mime_words(fn))
    return names

def parse_eml_for_meili(filepath):
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

        subject          = decode_mime_words(msg.get("subject", ""))
        from_            = decode_mime_words(msg.get("from", ""))
        to_              = decode_mime_words(msg.get("to", ""))
        date_            = msg.get("date", "")
        body             = extract_body_text(msg)
        attachment_names = get_attachment_names(msg)

        # Document ID: MD5 of filepath
        doc_id = hashlib.md5(filepath.encode()).hexdigest()

        return {
            "id":               doc_id,
            "filepath":         str(Path(filepath).relative_to(EMAIL_ROOT)),
            "category":         category,
            "person":           person,
            "subject":          subject,
            "from":             from_,
            "to":               to_,
            "date":             date_,
            "body":             body[:5000],   # Meili handles full text; cap at 5000 chars
            "attachment_names": attachment_names,
            "has_attachments":  len(attachment_names) > 0,
            "indexed_at":       datetime.now().isoformat(),
        }
    except Exception as e:
        log(f"  Parse error {Path(filepath).name}: {e}", "WARN")
        return None

# ── Meilisearch operations ────────────────────────────────────────────────────────
def meili_headers():
    return {"Authorization": f"Bearer {MEILI_KEY}", "Content-Type": "application/json"}

def ensure_index():
    """Create index with Japanese-friendly settings if not exists."""
    # Create index
    r = requests.post(
        f"{MEILI_URL}/indexes",
        headers=meili_headers(),
        json={"uid": INDEX_NAME, "primaryKey": "id"},
        timeout=10,
    )
    if r.status_code not in (200, 201, 202, 409):  # 202=async enqueued, 409=already exists
        log(f"  Index create status: {r.status_code} {r.text[:100]}", "WARN")
        return False

    # Configure searchable and filterable attributes
    settings = {
        "searchableAttributes": ["subject", "body", "from", "to", "attachment_names"],
        "filterableAttributes": ["category", "person", "has_attachments", "date"],
        "sortableAttributes":   ["date"],
        "displayedAttributes":  ["*"],
        "rankingRules": [
            "words", "typo", "proximity", "attribute", "sort", "exactness"
        ],
    }
    r2 = requests.patch(
        f"{MEILI_URL}/indexes/{INDEX_NAME}/settings",
        headers=meili_headers(),
        json=settings,
        timeout=10,
    )
    if not r2.ok:
        log(f"  Settings update: {r2.status_code}", "WARN")
    return True

def batch_index(docs):
    """Index a batch of documents to Meilisearch."""
    if not docs:
        return True
    try:
        r = requests.post(
            f"{MEILI_URL}/indexes/{INDEX_NAME}/documents",
            headers=meili_headers(),
            json=docs,
            timeout=30,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log(f"  Meili batch error: {e}", "WARN")
        return False

# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("  ingest_eml_to_meili.py (Phase3: keyword index)")
    log(f"  Meilisearch: {MEILI_URL}  Index: {INDEX_NAME}")
    log("=" * 60)

    # Check Meilisearch availability
    try:
        r = requests.get(f"{MEILI_URL}/health", timeout=5)
        if r.status_code != 200:
            log(f"Meilisearch not healthy: {r.status_code}", "ERROR")
            return
    except Exception as e:
        log(f"Meilisearch unreachable: {e}", "ERROR")
        return

    if not ensure_index():
        log("Failed to ensure Meilisearch index", "ERROR")
        return

    meili_state = load_meili_state()
    indexed     = meili_state.setdefault("indexed", {})

    all_emls = sorted(Path(EMAIL_ROOT).rglob("*.eml"))
    pending  = [p for p in all_emls if str(p) not in indexed]
    log(f"  Total: {len(all_emls)}  Pending: {len(pending)}")

    if not pending:
        log("  ✅ 新規なし。")
        return

    ok = skip = err = 0
    doc_buf = []

    for i, path in enumerate(pending):
        try:
            doc = parse_eml_for_meili(str(path))
            if not doc:
                indexed[str(path)] = {"error": "parse_failed", "ts": datetime.now().isoformat()}
                skip += 1
                continue

            doc_buf.append(doc)
            indexed[str(path)] = {"subject": doc["subject"][:80], "ts": datetime.now().isoformat()}

            if len(doc_buf) >= BATCH_SIZE:
                if batch_index(doc_buf):
                    ok += len(doc_buf)
                else:
                    err += len(doc_buf)
                doc_buf = []

        except Exception as e:
            log(f"  ERROR {path.name}: {e}", "ERROR")
            indexed[str(path)] = {"error": str(e), "ts": datetime.now().isoformat()}
            err += 1

        if (i + 1) % LOG_INTERVAL == 0:
            if doc_buf:
                if batch_index(doc_buf):
                    ok += len(doc_buf)
                doc_buf = []
            meili_state["indexed"] = indexed
            save_meili_state(meili_state)
            pct = (i + 1) / len(pending) * 100
            log(f"  [{i+1}/{len(pending)}] {pct:.1f}%  ok={ok}  skip={skip}  err={err}")

    if doc_buf:
        if batch_index(doc_buf):
            ok += len(doc_buf)
    meili_state["indexed"] = indexed
    save_meili_state(meili_state)

    total = requests.get(f"{MEILI_URL}/indexes/{INDEX_NAME}/stats",
                         headers=meili_headers(), timeout=10).json().get("numberOfDocuments", "?")
    log(f"  ✅ 完了: ok={ok}  skip={skip}  err={err}")
    log(f"  Meilisearch '{INDEX_NAME}' total docs: {total}")

if __name__ == "__main__":
    main()
