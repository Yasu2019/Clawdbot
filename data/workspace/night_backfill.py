"""
night_backfill.py — P016 Ollama夜間バックフィルデーモン
00:00〜05:00 JST の間、未完了メールをOllamaで継続解析する。
05:00を過ぎると自動終了。
"""
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta

import requests

JST = timezone(timedelta(hours=9))
STOP_HOUR_JST = 5   # 05:00 JSTで自動終了
SLEEP_BETWEEN = 3   # Ollama呼び出し間のスリープ秒数（過負荷防止）
SLEEP_IDLE = 30     # 対象なしの場合のスリープ秒数

BASE_WORKSPACE = os.getenv("P016_WORKSPACE", "/home/node/clawd")
DB_FILE = os.path.join(BASE_WORKSPACE, "email_analysis.db")
LOCAL_EMAIL_DIR = "/local_emails"
PAPERLESS_EMAIL_DIR = os.path.join(BASE_WORKSPACE, "paperless_consume", "email")
LOG_FILE = os.path.join(BASE_WORKSPACE, "night_backfill.log")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_TIMEOUT = 90
PREFERRED_OLLAMA_MODELS = [
    os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b"),
    "qwen2.5-coder:7b",
]

UNKNOWN = "不明"
NO_RESPONSE = "回答待ち"
_MODEL_CACHE = {"model": None}


def log(msg):
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def is_stop_time():
    now = datetime.now(JST)
    return now.hour >= STOP_HOUR_JST


def select_model():
    if _MODEL_CACHE["model"]:
        return _MODEL_CACHE["model"]
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=15)
        models = {m["name"] for m in resp.json().get("models", [])}
        for candidate in PREFERRED_OLLAMA_MODELS:
            if candidate in models:
                _MODEL_CACHE["model"] = candidate
                return candidate
    except Exception as e:
        log(f"Ollama tags error: {e}")
    return None


def get_backfill_targets(batch=10):
    if not os.path.exists(DB_FILE):
        return []
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT filepath FROM analyses
        WHERE is_resolved = 0
          AND (
              responder IS NULL OR responder IN ('', '-', '不明', 'Unknown')
              OR response_date IS NULL OR response_date IN ('', '-', '不明', 'Unknown')
              OR request_item IS NULL OR request_item IN ('', '-')
          )
        ORDER BY processed_at ASC
        LIMIT ?
    """, (batch,))
    rows = [r["filepath"] for r in c.fetchall()]
    conn.close()
    return rows


def resolve_path(filepath):
    if filepath and os.path.exists(filepath):
        return filepath
    if filepath and filepath.startswith("/local_emails/"):
        mapped = os.path.join(PAPERLESS_EMAIL_DIR, filepath[len("/local_emails/"):])
        if os.path.exists(mapped):
            return mapped
    return None


def build_prompt(email_data):
    body = email_data["body"][:1200]
    attachment_text = ", ".join(email_data["attachments"]) if email_data.get("attachments") else "なし"
    return f"""あなたはメールの事実抽出器です。推測は禁止です。以下の日本語メールから、ToDo 管理に必要な事実だけを JSON で抽出してください。

[メール情報]
from: {email_data['from']}
to: {email_data['to']}
date: {email_data['date']}
subject: {email_data['subject']}
attachments: {attachment_text}

[本文]
{body}

[ルール]
- JSON のみを返す
- キーは必ず英語
- 情報が無い場合は "-"
- request_item: 依頼内容を簡潔に
- deadline: 依頼期日
- response: 回答がある場合のみ。無い場合は "回答待ち"
- responder: 回答者
- response_date: 回答日
- importance: 高/中/低

Output JSON only:
{{"request_item":"string","deadline":"string","response":"string","responder":"string","response_date":"string","importance":"高|中|低","kaizen":"string","summary":"string"}}""".strip()


def parse_eml_simple(filepath):
    """シンプルなEMLパース（ingest_emails.pyと同じロジック）"""
    from email import policy
    from email.header import decode_header
    from email.parser import BytesParser
    from email.utils import getaddresses, parsedate_to_datetime
    import re

    def decode_mime(val):
        if not val:
            return ""
        parts = []
        try:
            for chunk, enc in decode_header(str(val)):
                if isinstance(chunk, bytes):
                    parts.append(chunk.decode(enc or "utf-8", errors="ignore"))
                else:
                    parts.append(chunk)
        except Exception:
            return str(val).strip()
        return "".join(parts).strip()

    try:
        with open(filepath, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
        subject = decode_mime(msg.get("subject", "No Subject"))
        from_raw = decode_mime(msg.get("from", UNKNOWN))
        to_raw = decode_mime(msg.get("to", UNKNOWN))
        date_raw = decode_mime(msg.get("date", UNKNOWN))
        try:
            date = parsedate_to_datetime(date_raw).strftime("%Y-%m-%d %H:%M")
        except Exception:
            date = date_raw

        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() != "text":
                    continue
                if "attachment" in str(part.get("Content-Disposition", "")).lower():
                    continue
                try:
                    payload = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        payload = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                if part.get_content_type() == "text/plain" and payload:
                    body_parts.append(str(payload))
        else:
            try:
                payload = msg.get_content()
            except Exception:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    payload = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
            if payload:
                body_parts.append(str(payload))

        body = "\n".join(p.strip() for p in body_parts if p and str(p).strip())
        name_addr = getaddresses([from_raw])
        from_name = name_addr[0][0] or name_addr[0][1] if name_addr else from_raw
        return {
            "subject": subject,
            "from": from_name.strip() or UNKNOWN,
            "to": to_raw,
            "date": date,
            "body": body.strip(),
            "attachments": [],
        }
    except Exception as e:
        log(f"  Parse error {filepath}: {e}")
        return None


def analyze_with_ollama(email_data):
    model = select_model()
    if not model:
        return None
    prompt = build_prompt(email_data)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0, "num_ctx": 1536},
    }
    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return json.loads(resp.json().get("response", "{}"))
    except Exception as e:
        log(f"  Ollama error: {e}")
        return None


def update_db(filepath, analysis, email_data):
    if not analysis or not isinstance(analysis, dict):
        return False

    def s(v, fallback="-"):
        if not v:
            return fallback
        t = str(v).replace("\r", " ").replace("\n", " ").strip()
        return t if t else fallback

    request_item = s(analysis.get("request_item") or analysis.get("依頼内容"))
    if request_item in ("-", "string", ""):
        request_item = s(email_data.get("subject"), fallback="-")
    response = s(analysis.get("response") or analysis.get("回答内容"), fallback=NO_RESPONSE)
    responder = s(analysis.get("responder") or analysis.get("回答者"), fallback=UNKNOWN)
    response_date = s(analysis.get("response_date") or analysis.get("回答日"), fallback=UNKNOWN)
    importance = s(analysis.get("importance") or analysis.get("重要度"), fallback="中")
    deadline = s(analysis.get("deadline") or analysis.get("依頼期日"), fallback=UNKNOWN)
    summary = s(analysis.get("summary"), fallback=request_item)

    resolved_markers = ("対応済", "回答済", "完了", "resolved", "done")
    is_resolved = 1 if response not in (NO_RESPONSE, "-") else 0
    if any(m.lower() in response.lower() for m in resolved_markers):
        is_resolved = 1
    if responder == UNKNOWN and response_date == UNKNOWN and response == NO_RESPONSE:
        is_resolved = 0

    conn = sqlite3.connect(DB_FILE, timeout=30)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        UPDATE analyses SET
            request_item = ?,
            deadline = ?,
            response = ?,
            responder = ?,
            response_date = ?,
            importance = ?,
            summary = ?,
            is_resolved = ?,
            processed_at = CURRENT_TIMESTAMP
        WHERE filepath = ?
    """, (request_item, deadline, response, responder, response_date, importance, summary, is_resolved, filepath))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def count_pending():
    if not os.path.exists(DB_FILE):
        return 0
    conn = sqlite3.connect(DB_FILE, timeout=30)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM analyses WHERE is_resolved=0")
    n = c.fetchone()[0]
    conn.close()
    return n


def main():
    log("=" * 50)
    log("Night Backfill Daemon 起動")
    log(f"停止予定: {STOP_HOUR_JST:02d}:00 JST")
    log("=" * 50)

    total = 0
    errors = 0

    while True:
        if is_stop_time():
            log(f"05:00 JST到達 — 自動終了。処理件数: {total}件")
            break

        targets = get_backfill_targets(batch=10)
        if not targets:
            pending = count_pending()
            log(f"対象なし（未完了残り: {pending}件）。{SLEEP_IDLE}秒待機...")
            time.sleep(SLEEP_IDLE)
            continue

        for filepath in targets:
            if is_stop_time():
                break

            source_path = resolve_path(filepath)
            if not source_path:
                log(f"  ファイルなし: {filepath}")
                errors += 1
                # Mark as resolved to skip next time
                conn = sqlite3.connect(DB_FILE, timeout=30)
                conn.execute("UPDATE analyses SET is_resolved=1 WHERE filepath=?", (filepath,))
                conn.commit()
                conn.close()
                continue

            email_data = parse_eml_simple(source_path)
            if not email_data:
                errors += 1
                continue

            basename = os.path.basename(source_path)
            log(f"  解析中: {basename[:60]}")
            analysis = analyze_with_ollama(email_data)
            if analysis:
                ok = update_db(filepath, analysis, email_data)
                if ok:
                    total += 1
                    log(f"  → 更新OK (計{total}件)")
                else:
                    log(f"  → DB更新失敗")
            else:
                errors += 1
                log(f"  → Ollama失敗")

            time.sleep(SLEEP_BETWEEN)

    log(f"完了: 成功={total}件 / エラー={errors}件")


if __name__ == "__main__":
    main()
