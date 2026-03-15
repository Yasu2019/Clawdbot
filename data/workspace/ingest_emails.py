import glob
import json
import os
import re
import sqlite3
from datetime import datetime
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

import requests


def detect_base_workspace():
    candidates = [
        os.getenv("P016_WORKSPACE"),
        "/workspace",
        "/home/node/clawd",
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return os.getcwd()


BASE_WORKSPACE = detect_base_workspace()
EMAIL_DIR = os.path.join(BASE_WORKSPACE, "temp_eml")
LOCAL_EMAIL_DIR = "/local_emails"
PAPERLESS_EMAIL_DIR = os.path.join(BASE_WORKSPACE, "paperless_consume", "email")
REPORT_FILE = os.path.join(BASE_WORKSPACE, "Email_Analysis_Report.md")
TRACKER_FILE = os.path.join(BASE_WORKSPACE, "processed_emails.json")
DB_FILE = os.path.join(BASE_WORKSPACE, "email_analysis.db")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_TIMEOUT = 60
PREFERRED_OLLAMA_MODELS = [
    os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b"),
    "qwen2.5-coder:7b",
]
CUTOFF_DATE = datetime(2025, 1, 1).timestamp()
NEW_EMAIL_LIMIT = None  # no limit — heuristic is fast, process all new emails per run
BACKFILL_LIMIT = 5  # Ollama re-analysis per run (~5 min worst case); night_backfill.py handles unlimited

UNKNOWN = "不明"
NO_RESPONSE = "回答待ち"
OLLAMA_MODEL_CACHE = {"base_url": None, "model": None}


LEGACY_KEY_MAP = {
    "request_item": ["request_item", "request", "依頼内容", "要件", "概要", "summary"],
    "deadline": ["deadline", "due_date", "依頼期日", "期限", "回答期限"],
    "response": ["response", "answer", "回答内容", "返信内容"],
    "responder": ["responder", "answerer", "回答者", "reply_from"],
    "response_date": ["response_date", "answered_at", "回答日", "reply_date"],
    "importance": ["importance", "priority", "重要度", "priority_level"],
    "kaizen": ["kaizen", "改善提案", "improvement"],
    "summary": ["summary", "要約"],
}


def decode_mime_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    parts = []
    try:
        for chunk, encoding in decode_header(value):
            if isinstance(chunk, bytes):
                parts.append(chunk.decode(encoding or "utf-8", errors="ignore"))
            else:
                parts.append(chunk)
    except Exception:
        return value.strip()
    return "".join(parts).strip()


def looks_garbled(text):
    if text is None:
        return False
    s = str(text).strip()
    if not s:
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?", s):
        return False
    if re.fullmatch(r"[A-Z][a-z]{2}, \d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}(:\d{2})? [+-]\d{4}", s):
        return False
    markers = ("Jd=~", "=?UTF-8?", "=?ISO-2022-JP?", "$N", "$r", "・ｽ", "FbIt4F::", "0w650")
    if any(marker in s for marker in markers):
        return True
    weird = sum(1 for ch in s if ch in "~$%^*_=\t\\")
    if weird >= 4 and weird >= max(1, len(s) // 6):
        return True
    if re.search(r"[A-Za-z]{2,}[=:;,]{1,}[A-Za-z0-9]{1,}", s):
        return True
    return False


def sanitize_text(value, fallback="-"):
    if value is None:
        return fallback
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return fallback
    if looks_garbled(text):
        return fallback
    return text


def truncate_text(text, limit):
    text = sanitize_text(text, fallback="-")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def normalize_subject(subject):
    return re.sub(r"^(re|fw|fwd)\s*[:!]\s*", "", subject, flags=re.IGNORECASE).strip()


def clean_body_line(line):
    cleaned = sanitize_text(line, fallback="-")
    cleaned = re.sub(r"^[>\s]+", "", cleaned).strip()
    cleaned = re.sub(r"^(Re|RE|Fw|FW|Fwd|FWD)\s*[:!]\s*", "", cleaned)
    if cleaned == "-":
        return ""
    return cleaned


def extract_reply_excerpt(body):
    if not body:
        return ""
    stop_markers = [
        "-----Original Message-----",
        "From:",
        "Sent:",
        "To:",
        "Subject:",
        "On ",
        "wrote:",
    ]
    lines = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(marker in line for marker in stop_markers):
            break
        if line.startswith(">"):
            break
        cleaned = clean_body_line(line)
        if not cleaned:
            continue
        if re.fullmatch(r"[\w.\-]+@[\w.\-]+", cleaned):
            continue
        if cleaned in {"いつもありがとうございます。", "お世話になっております。", "よろしくお願いいたします。", "ご確認ください。"}:
            continue
        lines.append(cleaned)
    if not lines:
        return ""
    return truncate_text(" ".join(lines[:3]), 120)


def extract_deadline(text):
    if not text:
        return UNKNOWN
    deadline_lines = []
    for raw_line in text.splitlines():
        line = sanitize_text(raw_line, fallback="-")
        if line == "-":
            continue
        if any(keyword in line for keyword in ["期限", "締切", "まで", "納期", "期日", "due"]):
            deadline_lines.append(line)
    if not deadline_lines:
        return UNKNOWN
    target = " ".join(deadline_lines[:3])
    patterns = [
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        r"(\d{1,2}[/-]\d{1,2})",
        r"(\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, target)
        if match:
            return sanitize_text(match.group(1), fallback=UNKNOWN)
    return UNKNOWN


def infer_importance(text):
    source = sanitize_text(text, fallback="")
    if any(keyword in source for keyword in ["至急", "緊急", "本日", "今日中", "至急対応", "急ぎ"]):
        return "高"
    if any(keyword in source for keyword in ["ご確認", "お願いします", "依頼", "回答"]):
        return "中"
    return "低"


def normalize_display_name(raw_value):
    decoded = decode_mime_text(raw_value)
    name_addr = getaddresses([decoded])
    if not name_addr:
        return sanitize_text(decoded, fallback=UNKNOWN)
    name, address = name_addr[0]
    name = sanitize_text(name, fallback="-")
    address = sanitize_text(address, fallback="-")
    if name not in {"-", UNKNOWN}:
        return name
    if address != "-":
        return address
    return sanitize_text(decoded, fallback=UNKNOWN)


def parse_email_date(raw_value, fallback=UNKNOWN):
    decoded = decode_mime_text(raw_value)
    try:
        return parsedate_to_datetime(decoded).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return sanitize_text(decoded, fallback=fallback)


def format_timestamp(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return UNKNOWN


def is_missing_value(value):
    return sanitize_text(value, fallback="-") in {"-", UNKNOWN, "Unknown", "None"}


def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30000)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE,
            email_date TEXT,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            request_item TEXT,
            deadline TEXT,
            response TEXT,
            responder TEXT,
            response_date TEXT,
            importance TEXT,
            kaizen TEXT,
            summary TEXT,
            is_resolved INTEGER DEFAULT 0,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing = {row[1] for row in c.execute("PRAGMA table_info(analyses)").fetchall()}
    if "responder" not in existing:
        c.execute("ALTER TABLE analyses ADD COLUMN responder TEXT")
    if "response_date" not in existing:
        c.execute("ALTER TABLE analyses ADD COLUMN response_date TEXT")
    conn.commit()
    conn.close()


def load_tracker():
    if not os.path.exists(TRACKER_FILE):
        return {}
    try:
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def fetch_existing_record(filepath):
    if not os.path.exists(DB_FILE):
        return None
    conn = sqlite3.connect(DB_FILE, timeout=30000)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM analyses WHERE filepath = ?", (filepath,))
    row = c.fetchone()
    conn.close()
    return row


def should_reprocess(filepath):
    row = fetch_existing_record(filepath)
    if row is None:
        return True
    request_item = sanitize_text(row["request_item"], fallback="-")
    responder = sanitize_text(row["responder"], fallback="-")
    response_date = sanitize_text(row["response_date"], fallback="-")
    if request_item == "-" or looks_garbled(row["request_item"]):
        return True
    if is_missing_value(responder) or is_missing_value(response_date):
        return True
    return False


def resolve_source_path(db_filepath):
    if db_filepath and os.path.exists(db_filepath):
        return db_filepath
    if db_filepath and db_filepath.startswith("/local_emails/"):
        suffix = db_filepath[len("/local_emails/") :]
        mapped = os.path.join(PAPERLESS_EMAIL_DIR, suffix)
        if os.path.exists(mapped):
            return mapped
    return None


def normalize_analysis(analysis, email_data):
    if not isinstance(analysis, dict):
        analysis = {}

    normalized = {}
    for target_key, aliases in LEGACY_KEY_MAP.items():
        value = None
        for alias in aliases:
            if alias in analysis and analysis[alias] not in (None, ""):
                value = analysis[alias]
                break
        normalized[target_key] = sanitize_text(value, fallback="-")

    subject_core = normalize_subject(email_data["subject"])
    if normalized["request_item"] == "-":
        normalized["request_item"] = truncate_text(subject_core or email_data["subject"], 120)
    if normalized["summary"] == "-":
        normalized["summary"] = normalized["request_item"]
    if normalized["deadline"] == "-":
        normalized["deadline"] = UNKNOWN
    if normalized["importance"] == "-":
        normalized["importance"] = "中"
    if normalized["kaizen"] == "-":
        normalized["kaizen"] = "-"

    is_reply = bool(re.match(r"^(re|fw|fwd)\s*[:!]", email_data["subject"], flags=re.IGNORECASE))
    if normalized["response"] == "-":
        normalized["response"] = NO_RESPONSE
    if normalized["response"] != NO_RESPONSE and is_missing_value(normalized["responder"]):
        normalized["responder"] = email_data["from"]
    if normalized["response"] != NO_RESPONSE and is_missing_value(normalized["response_date"]):
        normalized["response_date"] = email_data["date"]
    if is_reply and normalized["response"] == NO_RESPONSE:
        normalized["response"] = truncate_text(subject_core or email_data["body"], 80)
    if is_reply and is_missing_value(normalized["responder"]):
        normalized["responder"] = email_data["from"]
    if is_reply and is_missing_value(normalized["response_date"]):
        normalized["response_date"] = email_data["date"]

    if is_missing_value(normalized["responder"]):
        normalized["responder"] = UNKNOWN
    if is_missing_value(normalized["response_date"]):
        normalized["response_date"] = UNKNOWN

    return normalized


def analysis_is_usable(analysis):
    if not isinstance(analysis, dict):
        return False
    request_item = sanitize_text(analysis.get("request_item"), fallback="-")
    if request_item in {"-", "string"}:
        return False
    if looks_garbled(request_item):
        return False
    response = sanitize_text(analysis.get("response"), fallback="-")
    if response == "string":
        return False
    return True


def select_ollama_model():
    if OLLAMA_MODEL_CACHE["base_url"] == OLLAMA_BASE_URL and OLLAMA_MODEL_CACHE["model"]:
        return OLLAMA_MODEL_CACHE["model"]
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        models = {item.get("name") for item in payload.get("models", [])}
        for candidate in PREFERRED_OLLAMA_MODELS:
            if candidate in models:
                OLLAMA_MODEL_CACHE["base_url"] = OLLAMA_BASE_URL
                OLLAMA_MODEL_CACHE["model"] = candidate
                return candidate
    except Exception as e:
        print(f"  Ollama tags lookup failed: {e}")
    return None


def save_to_db(email_data, analysis):
    normalized = normalize_analysis(analysis, email_data)
    resolved_markers = ("対応済", "回答済", "完了", "resolved", "done")
    is_resolved = 0
    if normalized["response"] != NO_RESPONSE:
        is_resolved = 1
    if any(marker.lower() in normalized["response"].lower() for marker in resolved_markers):
        is_resolved = 1
    if normalized["responder"] == UNKNOWN or normalized["response_date"] == UNKNOWN:
        if normalized["response"] == NO_RESPONSE:
            is_resolved = 0

    conn = sqlite3.connect(DB_FILE, timeout=30000)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute(
        """
        INSERT OR REPLACE INTO analyses
        (filepath, email_date, sender, recipient, subject, request_item, deadline, response, responder, response_date, importance, kaizen, summary, is_resolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email_data["path"],
            sanitize_text(email_data["date"], fallback=UNKNOWN),
            sanitize_text(email_data["from"], fallback=UNKNOWN),
            sanitize_text(email_data["to"], fallback=UNKNOWN),
            sanitize_text(email_data["subject"], fallback="No Subject"),
            normalized["request_item"],
            normalized["deadline"],
            normalized["response"],
            normalized["responder"],
            normalized["response_date"],
            normalized["importance"],
            normalized["kaizen"],
            normalized["summary"],
            is_resolved,
        ),
    )
    conn.commit()
    conn.close()


def get_pending_tasks(limit=50):
    if not os.path.exists(DB_FILE):
        return []
    conn = sqlite3.connect(DB_FILE, timeout=30000)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute(
        """
        SELECT *
        FROM analyses
        WHERE is_resolved = 0
        ORDER BY processed_at DESC, email_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def parse_eml(filepath):
    try:
        with open(filepath, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        subject = decode_mime_text(msg.get("subject", "No Subject"))
        from_ = normalize_display_name(msg.get("from", UNKNOWN))
        to = normalize_display_name(msg.get("to", UNKNOWN))
        date = parse_email_date(msg.get("date", UNKNOWN))

        body_parts = []
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()
                if filename:
                    attachments.append(decode_mime_text(filename))
                if part.get_content_maintype() != "text":
                    continue
                if "attachment" in content_disposition.lower():
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

        body = "\n".join(part.strip() for part in body_parts if part and str(part).strip())
        return {
            "subject": sanitize_text(subject, fallback="No Subject"),
            "from": sanitize_text(from_, fallback=UNKNOWN),
            "to": sanitize_text(to, fallback=UNKNOWN),
            "date": sanitize_text(date, fallback=UNKNOWN),
            "body": body.strip(),
            "attachments": [sanitize_text(name, fallback="-") for name in attachments],
        }
    except Exception as e:
        print(f"  Parse error {filepath}: {e}")
        return None


def build_prompt(email_data):
    attachment_text = ", ".join(email_data["attachments"]) if email_data["attachments"] else "なし"
    body = email_data["body"][:1200]
    return f"""
あなたはメールの事実抽出器です。推測は禁止です。以下の日本語メールから、ToDo 管理に必要な事実だけを JSON で抽出してください。

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
- キーは必ず英語で返す
- 情報が無い場合は \"-\"
- \"string\" などのプレースホルダは禁止
- 一般論や説明は禁止
- request_item は依頼内容を簡潔にまとめる
- deadline は依頼期日
- response は既に回答が含まれている場合のみ入れる。無い場合は \"回答待ち\"
- responder は回答者
- response_date は回答日
- importance は 高, 中, 低 のいずれか

[例]
Input:
from: a@example.com
date: 2026-03-01 10:00
subject: RE: 見積書送付のお願い
body: 見積書を添付します。ご確認ください。
Output:
{{"request_item":"見積書送付のお願い","deadline":"-","response":"見積書を添付して送付した","responder":"a@example.com","response_date":"2026-03-01 10:00","importance":"中","kaizen":"-","summary":"見積書送付のお願いに回答"}}

{{
  "request_item": "string",
  "deadline": "string",
  "response": "string",
  "responder": "string",
  "response_date": "string",
  "importance": "高|中|低",
  "kaizen": "string",
  "summary": "string"
}}
""".strip()


def heuristic_analysis(email_data):
    subject = sanitize_text(email_data["subject"], fallback="No Subject")
    body = sanitize_text(email_data["body"], fallback="-")
    subject_core = normalize_subject(subject)
    request_item = truncate_text(subject_core or subject, 120)
    is_reply = bool(re.match(r"^(re|fw|fwd)\s*[:!]", subject, flags=re.IGNORECASE))
    response_excerpt = extract_reply_excerpt(email_data["body"])
    deadline = extract_deadline(email_data["body"])
    importance = infer_importance(" ".join([subject, body]))

    analysis = {
        "request_item": request_item,
        "deadline": deadline,
        "response": NO_RESPONSE,
        "responder": UNKNOWN,
        "response_date": UNKNOWN,
        "importance": importance,
        "kaizen": "-",
        "summary": request_item,
    }

    if is_reply:
        analysis["response"] = response_excerpt or truncate_text(subject_core or body, 80)
        analysis["responder"] = sanitize_text(email_data["from"], fallback=UNKNOWN)
        analysis["response_date"] = sanitize_text(email_data["date"], fallback=UNKNOWN)

    return analysis


def analyze_with_ollama(email_data):
    prompt = build_prompt(email_data)
    heuristic = heuristic_analysis(email_data)
    is_reply = bool(re.match(r"^(re|fw|fwd)\s*[:!]", email_data["subject"], flags=re.IGNORECASE))
    if is_reply and heuristic["response"] != NO_RESPONSE:
        return heuristic
    model = select_ollama_model()
    if not model:
        return heuristic
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
        raw = resp.json().get("response", "{}")
        parsed = json.loads(raw)
        normalized = normalize_analysis(parsed, email_data)
        if analysis_is_usable(normalized):
            if normalized["response"] == NO_RESPONSE and heuristic["response"] != NO_RESPONSE:
                normalized["response"] = heuristic["response"]
                normalized["responder"] = heuristic["responder"]
                normalized["response_date"] = heuristic["response_date"]
            if normalized["deadline"] == UNKNOWN and heuristic["deadline"] != UNKNOWN:
                normalized["deadline"] = heuristic["deadline"]
            if normalized["importance"] in {"-", "中"} and heuristic["importance"] != "中":
                normalized["importance"] = heuristic["importance"]
            return normalized
        return heuristic
    except Exception as e:
        print(f"  Ollama Error: {e}")
        return heuristic


def format_report_row(row):
    sender = sanitize_text(row["sender"], fallback="-")
    request_item = sanitize_text(row["request_item"], fallback="-")
    if request_item == "-":
        request_item = sanitize_text(row["summary"], fallback="-")
    if sender == "-" or looks_garbled(sender) or request_item == "-" or looks_garbled(request_item):
        return None
    return {
        "email_date": truncate_text(row["email_date"], 20),
        "sender": truncate_text(sender, 32),
        "request_item": truncate_text(request_item, 90),
        "deadline": sanitize_text(row["deadline"], fallback=UNKNOWN),
        "response": truncate_text(row["response"], 36),
        "responder": truncate_text(row["responder"], 24),
        "response_date": truncate_text(row["response_date"], 20),
        "importance": sanitize_text(row["importance"], fallback="中"),
    }


def generate_report(total_processed):
    pending = []
    for row in get_pending_tasks():
        formatted = format_report_row(row)
        if formatted:
            pending.append(formatted)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# P016 Email ToDo レポート\n\n")
        if pending:
            f.write("## 未完了案件\n\n")
            f.write("| 依頼日 | 依頼者 | 依頼内容 | 依頼期日 | 回答内容 | 回答者 | 回答日 | 重要度 |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for row in pending:
                f.write(
                    f"| {row['email_date']} | {row['sender']} | {row['request_item']} | "
                    f"{row['deadline']} | {row['response']} | {row['responder']} | "
                    f"{row['response_date']} | {row['importance']} |\n"
                )
            f.write("\n")
        else:
            f.write("## 未完了案件はありません\n\n")

        f.write("## 処理結果\n\n")
        if total_processed > 0:
            f.write(f"- 今回の再解析件数: {total_processed} 件\n")
        else:
            f.write("- 今回の再解析件数: 0 件\n")

    print(f"  Report updated ({total_processed} processed).")


def collect_candidate_emails(tracker):
    all_emls = []
    if os.path.exists(EMAIL_DIR):
        for path in glob.glob(os.path.join(EMAIL_DIR, "*.eml")):
            if path not in tracker or should_reprocess(path):
                all_emls.append({"path": path, "mtime": os.path.getmtime(path)})

    if os.path.exists(LOCAL_EMAIL_DIR):
        for path in glob.glob(os.path.join(LOCAL_EMAIL_DIR, "**/*.eml"), recursive=True):
            mtime = os.path.getmtime(path)
            if mtime < CUTOFF_DATE:
                continue
            if path not in tracker or should_reprocess(path):
                all_emls.append({"path": path, "mtime": mtime})

    if os.path.exists(PAPERLESS_EMAIL_DIR):
        for path in glob.glob(os.path.join(PAPERLESS_EMAIL_DIR, "**/*.eml"), recursive=True):
            mtime = os.path.getmtime(path)
            if mtime < CUTOFF_DATE:
                continue
            if path not in tracker or should_reprocess(path):
                all_emls.append({"path": path, "mtime": mtime})

    unique = {}
    for item in all_emls:
        unique[item["path"]] = item
    result = list(unique.values())
    result.sort(key=lambda x: x["mtime"], reverse=True)
    return result if NEW_EMAIL_LIMIT is None else result[:NEW_EMAIL_LIMIT]


def collect_backfill_targets(limit=BACKFILL_LIMIT):
    if not os.path.exists(DB_FILE):
        return []

    conn = sqlite3.connect(DB_FILE, timeout=30000)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """
        SELECT filepath
        FROM analyses
        WHERE is_resolved = 0
          AND (
              responder IS NULL OR responder = '' OR responder IN ('-', '不明', 'Unknown')
              OR response_date IS NULL OR response_date = '' OR response_date IN ('-', '不明', 'Unknown')
              OR request_item IS NULL OR request_item = '' OR request_item IN ('-')
          )
        ORDER BY processed_at DESC, email_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = c.fetchall()
    conn.close()

    targets = []
    for row in rows:
        filepath = row["filepath"]
        source_path = resolve_source_path(filepath)
        if not source_path:
            continue
        targets.append(
            {
                "path": filepath,
                "source_path": source_path,
                "mtime": os.path.getmtime(source_path),
            }
        )

    deduped = {}
    for item in targets:
        deduped[item["path"]] = item
    result = list(deduped.values())
    result.sort(key=lambda x: x["mtime"], reverse=True)
    return result


def main():
    print("=" * 60)
    print("  Email Ingestion - P016 ToDo Ledger")
    print(f"  Workspace: {BASE_WORKSPACE}")
    print("=" * 60)

    init_db()
    tracker = load_tracker()
    new_emls = collect_candidate_emails(tracker)
    new_paths = {entry["path"] for entry in new_emls}
    backfill_emls = []
    for item in collect_backfill_targets():
        if item["path"] not in new_paths:
            item["_backfill"] = True
            backfill_emls.append(item)

    all_emls = new_emls + backfill_emls

    if not all_emls:
        pending = get_pending_tasks()
        if pending:
            print("\n  No new emails, but pending tasks exist.")
            generate_report(0)
        else:
            print("\n  No new emails to process.")
        return

    print(f"\n  Found {len(new_emls)} new + {len(backfill_emls)} backfill emails.")
    for index, item in enumerate(all_emls, 1):
        filepath = item["path"]
        source_path = item.get("source_path", filepath)
        basename = os.path.basename(source_path)
        is_backfill = item.get("_backfill", False)
        print(f"  [{index}/{len(all_emls)}] {'[BF] ' if is_backfill else ''}{basename[:65]}")

        email_data = parse_eml(source_path)
        if not email_data:
            continue
        if is_missing_value(email_data["date"]):
            email_data["date"] = format_timestamp(item["mtime"])
        email_data["path"] = filepath

        # New emails: heuristic only (fast bulk ingest); backfill: Ollama for quality improvement
        if is_backfill:
            analysis = analyze_with_ollama(email_data)
        else:
            analysis = heuristic_analysis(email_data)
        save_to_db(email_data, analysis)
        tracker[filepath] = item["mtime"]
        save_tracker(tracker)

        if index % 20 == 0:
            generate_report(index)

    generate_report(len(all_emls))
    print(f"\n  Processing complete. Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
