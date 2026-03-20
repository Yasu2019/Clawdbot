#!/usr/bin/env python3
"""
email_search_index.py

Indexes local EML files and Gmail messages into a single SQLite FTS database.

Default action:
  python3 /home/node/clawd/email_search_index.py

Search:
  python3 /home/node/clawd/email_search_index.py search "品質 会議"
"""

from __future__ import annotations

import argparse
import base64
import email
import hashlib
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests


WORKSPACE_ROOT = Path("/home/node/clawd")
EMAIL_ROOT = WORKSPACE_ROOT / "paperless_consume" / "email"
DB_PATH = WORKSPACE_ROOT / "email_search.db"
STATE_PATH = WORKSPACE_ROOT / "email_search_state.json"
STATUS_PATH = WORKSPACE_ROOT / "email_search_harness_status.json"
TOKEN_PATH = WORKSPACE_ROOT / "token.json"
LEGACY_TOKEN_PATH = Path("/home/node/clawd/../work/token.json")
CREDS_PATH = WORKSPACE_ROOT / "credentials.json"
LEGACY_CREDS_PATH = Path("/home/node/clawd/../workspace/credentials.json")
TIMEOUT = 30
USER_AGENT = "claw-email-search-index/1.0"
TASK_KEYWORDS = (
    "依頼",
    "お願い",
    "ご対応",
    "対応",
    "提出",
    "回答",
    "返信",
    "確認",
    "ご確認",
    "ご連絡",
    "送付",
    "締切",
    "期限",
    "期日",
    "至急",
)
REPLY_DONE_KEYWORDS = ("回答しました", "回答済", "送付しました", "送付済", "返信しました", "対応しました")
STATUS_OPEN = "open"
STATUS_REPLIED = "replied"
STATUS_UNKNOWN = "unknown"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def log(message: str) -> None:
    print(message, flush=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_status(payload: dict) -> None:
    save_json(STATUS_PATH, payload)


def decode_mime_words(value: Optional[str]) -> str:
    if not value:
        return ""
    chunks = []
    for raw, enc in decode_header(value):
        if isinstance(raw, bytes):
            for candidate in [enc or "utf-8", "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                try:
                    chunks.append(raw.decode(candidate))
                    break
                except Exception:
                    continue
            else:
                chunks.append(raw.decode("utf-8", errors="replace"))
        else:
            chunks.append(str(raw))
    return "".join(chunks).strip()


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", unescape(text))
    return text.strip()


def decode_bytes(payload: bytes, charset: Optional[str]) -> str:
    for candidate in [charset or "utf-8", "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
        try:
            return payload.decode(candidate)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def extract_body_and_attachments(msg: Message) -> Tuple[str, List[str]]:
    plain_parts: List[str] = []
    html_parts: List[str] = []
    attachments: List[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            filename = decode_mime_words(part.get_filename())
            if filename:
                attachments.append(filename)
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", "")).lower()
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            if content_type == "text/plain":
                plain_parts.append(decode_bytes(payload, part.get_content_charset()))
            elif content_type == "text/html":
                html_parts.append(html_to_text(decode_bytes(payload, part.get_content_charset())))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = decode_bytes(payload, msg.get_content_charset())
            if msg.get_content_type() == "text/html":
                html_parts.append(html_to_text(body))
            else:
                plain_parts.append(body)

    body = "\n\n".join([p.strip() for p in plain_parts if p.strip()]).strip()
    if not body:
        body = "\n\n".join([p.strip() for p in html_parts if p.strip()]).strip()
    return body, attachments


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_email_datetime(value: str) -> Optional[datetime]:
    text = normalize_space(value)
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def infer_thread_key(record: EmailRecord) -> str:
    if record.gmail_thread_id:
        return f"gmail:{record.gmail_thread_id}"
    if record.message_id_header:
        return normalize_space(record.message_id_header.lower())
    subject = normalize_space(record.subject.lower())
    subject = re.sub(r"^(re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE)
    return f"{normalize_space(record.sender.lower())}|{subject}"[:240]


def looks_like_task(record: EmailRecord) -> bool:
    haystack = normalize_space("\n".join([record.subject, record.body_text, record.snippet]))
    if any(keyword in haystack for keyword in TASK_KEYWORDS):
        return True
    return bool(re.search(r"(までに|期限|締切|期日|要約|提出|確認|回答|返信)", haystack))


def infer_relative_due_date(text: str, base_dt: datetime) -> Optional[datetime]:
    if "明日" in text:
        return base_dt + timedelta(days=1)
    if "今日" in text or "本日" in text:
        return base_dt
    if "明後日" in text:
        return base_dt + timedelta(days=2)
    if "来週" in text:
        return base_dt + timedelta(days=7)
    if "今週中" in text:
        return base_dt + timedelta(days=max(0, 4 - base_dt.weekday()))
    return None


def extract_due_date(text: str, base_dt: datetime) -> str:
    normalized = normalize_space(text)
    match = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", normalized)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", normalized)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.search(r"(?<!\d)(\d{1,2})[/-](\d{1,2})(?!\d)", normalized)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = base_dt.year
        try:
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate < base_dt - timedelta(days=32):
                candidate = datetime(year + 1, month, day, tzinfo=timezone.utc)
            return candidate.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    match = re.search(r"(?<!\d)(\d{1,2})月(\d{1,2})日", normalized)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = base_dt.year
        try:
            candidate = datetime(year, month, day, tzinfo=timezone.utc)
            if candidate < base_dt - timedelta(days=32):
                candidate = datetime(year + 1, month, day, tzinfo=timezone.utc)
            return candidate.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    relative = infer_relative_due_date(normalized, base_dt)
    return relative.strftime("%Y-%m-%d") if relative else ""


def extract_assignee(text: str) -> str:
    match = re.search(r"([一-龠々ぁ-んァ-ヶA-Za-z0-9._-]{2,40})(様|さん|殿|宛|ご担当)", text)
    if match:
        return normalize_space(match.group(1))
    return ""


def summarize_request(text: str) -> str:
    cleaned = normalize_space(text)
    if not cleaned:
        return ""
    for split_token in ("-----Original Message-----", "From:", "差出人:", "Sent:", "送信日時:"):
        if split_token in cleaned:
            cleaned = cleaned.split(split_token, 1)[0].strip()
    sentences = re.split(r"(?<=[。！？\n])", cleaned)
    summary = normalize_space("".join(sentences[:3]))
    return summary[:600]


def infer_reply_status(record: EmailRecord, body_summary: str) -> str:
    subject = normalize_space(record.subject)
    haystack = normalize_space(f"{subject}\n{body_summary}")
    if any(keyword in haystack for keyword in REPLY_DONE_KEYWORDS):
        return STATUS_REPLIED
    if subject.lower().startswith(("re:", "fw:", "fwd:")):
        return STATUS_REPLIED
    if "未回答" in haystack or "未返信" in haystack:
        return STATUS_OPEN
    return STATUS_UNKNOWN


def infer_status(reply_status: str, due_date: str) -> str:
    if reply_status == STATUS_REPLIED:
        return STATUS_REPLIED
    if due_date:
        return STATUS_OPEN
    return STATUS_UNKNOWN


def extract_task_record(record: EmailRecord) -> Optional[TaskRecord]:
    if not looks_like_task(record):
        return None
    body_summary = summarize_request(record.body_text or record.snippet)
    base_dt = parse_email_datetime(record.email_date) or datetime.now(timezone.utc)
    request_date = base_dt.astimezone().strftime("%Y-%m-%d")
    due_date = extract_due_date("\n".join([record.subject, body_summary]), base_dt)
    reply_status = infer_reply_status(record, body_summary)
    return TaskRecord(
        source=record.source,
        source_id=record.source_id,
        thread_key=infer_thread_key(record),
        request_date=request_date,
        due_date=due_date,
        requester=normalize_space(record.sender),
        assignee=extract_assignee("\n".join([record.recipients, record.cc, body_summary])),
        request_subject=normalize_space(record.subject)[:300],
        request_body=body_summary,
        status=infer_status(reply_status, due_date),
        reply_status=reply_status,
        replier=normalize_space(record.sender) if reply_status == STATUS_REPLIED else "",
        reply_summary=body_summary if reply_status == STATUS_REPLIED else "",
        evidence=json.dumps(
            {
                "message_id_header": record.message_id_header,
                "gmail_thread_id": record.gmail_thread_id,
                "snippet": normalize_space(record.snippet)[:280],
            },
            ensure_ascii=False,
        ),
    )


@dataclass
class EmailRecord:
    source: str
    source_id: str
    subject: str
    sender: str
    recipients: str
    cc: str
    email_date: str
    body_text: str
    attachment_names: List[str]
    filepath: str = ""
    category: str = ""
    person: str = ""
    gmail_thread_id: str = ""
    gmail_message_id: str = ""
    message_id_header: str = ""
    labels_json: str = "[]"
    internal_ts: int = 0
    snippet: str = ""
    body_hash: str = ""
    raw_sha1: str = ""


@dataclass
class TaskRecord:
    source: str
    source_id: str
    thread_key: str
    request_date: str
    due_date: str
    requester: str
    assignee: str
    request_subject: str
    request_body: str
    status: str
    reply_status: str
    replier: str
    reply_summary: str
    evidence: str


def email_record_from_row(row: sqlite3.Row) -> EmailRecord:
    try:
        attachment_names = json.loads(row["attachment_names"] or "[]")
    except Exception:
        attachment_names = []
    if not isinstance(attachment_names, list):
        attachment_names = []
    return EmailRecord(
        source=row["source"],
        source_id=row["source_id"],
        subject=row["subject"],
        sender=row["sender"],
        recipients=row["recipients"],
        cc=row["cc"],
        email_date=row["email_date"],
        body_text=row["body_text"],
        attachment_names=attachment_names,
        filepath=row["filepath"],
        category=row["category"],
        person=row["person"],
        gmail_thread_id=row["gmail_thread_id"],
        gmail_message_id=row["gmail_message_id"],
        message_id_header=row["message_id_header"],
        labels_json=row["labels_json"],
        internal_ts=row["internal_ts"],
        snippet=row["snippet"],
        body_hash=row["body_hash"],
        raw_sha1=row["raw_sha1"],
    )


def parse_eml(path: Path) -> EmailRecord:
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw)
    rel = path.relative_to(EMAIL_ROOT)
    parts = rel.parts
    category = parts[0] if len(parts) > 1 else ""
    person = parts[1] if len(parts) > 2 else ""
    body, attachments = extract_body_and_attachments(msg)
    source_id = str(rel).replace("\\", "/")
    return EmailRecord(
        source="eml",
        source_id=source_id,
        subject=decode_mime_words(msg.get("subject")),
        sender=decode_mime_words(msg.get("from")),
        recipients=decode_mime_words(msg.get("to")),
        cc=decode_mime_words(msg.get("cc")),
        email_date=decode_mime_words(msg.get("date")),
        body_text=body,
        attachment_names=attachments,
        filepath=source_id,
        category=category,
        person=person,
        message_id_header=decode_mime_words(msg.get("message-id")),
        snippet=body[:280],
        body_hash=hashlib.sha1(body.encode("utf-8", errors="ignore")).hexdigest(),
        raw_sha1=hashlib.sha1(raw).hexdigest(),
    )


def find_existing_path(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def refresh_gmail_token(token: dict, creds: dict) -> dict:
    installed = creds.get("installed") or creds.get("web") or {}
    response = requests.post(
        installed["token_uri"],
        headers={"User-Agent": USER_AGENT},
        data={
            "client_id": installed["client_id"],
            "client_secret": installed["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    refreshed = response.json()
    token["access_token"] = refreshed["access_token"]
    token["token_type"] = refreshed.get("token_type", token.get("token_type", "Bearer"))
    expires_in = int(refreshed.get("expires_in", 3600))
    token["expiry_date"] = int((time.time() + expires_in - 60) * 1000)
    return token


def gmail_session() -> Tuple[requests.Session, dict]:
    token_path = find_existing_path([TOKEN_PATH, LEGACY_TOKEN_PATH])
    creds_path = find_existing_path([CREDS_PATH, LEGACY_CREDS_PATH])
    if not token_path or not creds_path:
        raise FileNotFoundError("Gmail token or credentials file was not found")

    token = load_json(token_path)
    creds = load_json(creds_path)
    expiry_ms = int(token.get("expiry_date", 0))
    if not token.get("access_token") or expiry_ms <= int(time.time() * 1000):
        token = refresh_gmail_token(token, creds)
        save_json(token_path, token)

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token['access_token']}",
            "User-Agent": USER_AGENT,
        }
    )
    return session, token


def gmail_request(session: requests.Session, method: str, url: str, **kwargs) -> dict:
    response = session.request(method, url, timeout=TIMEOUT, **kwargs)
    if response.status_code == 401:
        raise RuntimeError("Gmail access token was rejected")
    response.raise_for_status()
    return response.json()


def parse_gmail_headers(payload: dict) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in payload.get("headers", []):
        name = item.get("name", "").lower()
        if name:
            result[name] = item.get("value", "")
    return result


def decode_base64url(data: str) -> str:
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(data + padding)
    return decode_bytes(raw, "utf-8")


def extract_gmail_parts(payload: dict) -> Tuple[str, List[str]]:
    plain_parts: List[str] = []
    html_parts: List[str] = []
    attachments: List[str] = []

    def walk(part: dict) -> None:
        filename = decode_mime_words(part.get("filename"))
        if filename:
            attachments.append(filename)
        body = part.get("body", {})
        mime = part.get("mimeType", "")
        data = body.get("data")
        if data:
            text = decode_base64url(data)
            if mime == "text/plain":
                plain_parts.append(text)
            elif mime == "text/html":
                html_parts.append(html_to_text(text))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    body = "\n\n".join([p.strip() for p in plain_parts if p.strip()]).strip()
    if not body:
        body = "\n\n".join([p.strip() for p in html_parts if p.strip()]).strip()
    return body, attachments


def parse_gmail_message(message: dict) -> EmailRecord:
    payload = message.get("payload", {})
    headers = parse_gmail_headers(payload)
    body, attachments = extract_gmail_parts(payload)
    snippet = message.get("snippet", "") or body[:280]
    body_hash = hashlib.sha1(body.encode("utf-8", errors="ignore")).hexdigest()
    raw_sha1 = hashlib.sha1(
        json.dumps(message, ensure_ascii=False, sort_keys=True).encode("utf-8", errors="ignore")
    ).hexdigest()
    return EmailRecord(
        source="gmail",
        source_id=message["id"],
        subject=decode_mime_words(headers.get("subject", "")),
        sender=decode_mime_words(headers.get("from", "")),
        recipients=decode_mime_words(headers.get("to", "")),
        cc=decode_mime_words(headers.get("cc", "")),
        email_date=decode_mime_words(headers.get("date", "")),
        body_text=body,
        attachment_names=attachments,
        gmail_thread_id=message.get("threadId", ""),
        gmail_message_id=message.get("id", ""),
        message_id_header=decode_mime_words(headers.get("message-id", "")),
        labels_json=json.dumps(message.get("labelIds", []), ensure_ascii=False),
        internal_ts=int(message.get("internalDate", "0") or 0),
        snippet=snippet,
        body_hash=body_hash,
        raw_sha1=raw_sha1,
    )


def connect_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT '',
            sender TEXT NOT NULL DEFAULT '',
            recipients TEXT NOT NULL DEFAULT '',
            cc TEXT NOT NULL DEFAULT '',
            email_date TEXT NOT NULL DEFAULT '',
            body_text TEXT NOT NULL DEFAULT '',
            attachment_names TEXT NOT NULL DEFAULT '',
            filepath TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            person TEXT NOT NULL DEFAULT '',
            gmail_thread_id TEXT NOT NULL DEFAULT '',
            gmail_message_id TEXT NOT NULL DEFAULT '',
            message_id_header TEXT NOT NULL DEFAULT '',
            labels_json TEXT NOT NULL DEFAULT '[]',
            internal_ts INTEGER NOT NULL DEFAULT 0,
            snippet TEXT NOT NULL DEFAULT '',
            body_hash TEXT NOT NULL DEFAULT '',
            raw_sha1 TEXT NOT NULL DEFAULT '',
            indexed_at TEXT NOT NULL,
            PRIMARY KEY (source, source_id)
        )
        """
    )
    con.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
            subject,
            sender,
            recipients,
            cc,
            body_text,
            attachment_names,
            content='emails',
            content_rowid='rowid',
            tokenize='unicode61'
        )
        """
    )
    con.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
            INSERT INTO emails_fts(rowid, subject, sender, recipients, cc, body_text, attachment_names)
            VALUES (new.rowid, new.subject, new.sender, new.recipients, new.cc, new.body_text, new.attachment_names);
        END;
        CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
            INSERT INTO emails_fts(emails_fts, rowid, subject, sender, recipients, cc, body_text, attachment_names)
            VALUES('delete', old.rowid, old.subject, old.sender, old.recipients, old.cc, old.body_text, old.attachment_names);
        END;
        CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
            INSERT INTO emails_fts(emails_fts, rowid, subject, sender, recipients, cc, body_text, attachment_names)
            VALUES('delete', old.rowid, old.subject, old.sender, old.recipients, old.cc, old.body_text, old.attachment_names);
            INSERT INTO emails_fts(rowid, subject, sender, recipients, cc, body_text, attachment_names)
            VALUES (new.rowid, new.subject, new.sender, new.recipients, new.cc, new.body_text, new.attachment_names);
        END;
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            thread_key TEXT NOT NULL DEFAULT '',
            request_date TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            requester TEXT NOT NULL DEFAULT '',
            assignee TEXT NOT NULL DEFAULT '',
            request_subject TEXT NOT NULL DEFAULT '',
            request_body TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '',
            reply_status TEXT NOT NULL DEFAULT '',
            replier TEXT NOT NULL DEFAULT '',
            reply_summary TEXT NOT NULL DEFAULT '',
            evidence TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (source, source_id),
            FOREIGN KEY (source, source_id) REFERENCES emails(source, source_id) ON DELETE CASCADE
        )
        """
    )
    con.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
            requester,
            assignee,
            request_subject,
            request_body,
            replier,
            reply_summary,
            content='tasks',
            content_rowid='rowid',
            tokenize='unicode61'
        )
        """
    )
    con.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
            INSERT INTO tasks_fts(rowid, requester, assignee, request_subject, request_body, replier, reply_summary)
            VALUES (new.rowid, new.requester, new.assignee, new.request_subject, new.request_body, new.replier, new.reply_summary);
        END;
        CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
            INSERT INTO tasks_fts(tasks_fts, rowid, requester, assignee, request_subject, request_body, replier, reply_summary)
            VALUES('delete', old.rowid, old.requester, old.assignee, old.request_subject, old.request_body, old.replier, old.reply_summary);
        END;
        CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
            INSERT INTO tasks_fts(tasks_fts, rowid, requester, assignee, request_subject, request_body, replier, reply_summary)
            VALUES('delete', old.rowid, old.requester, old.assignee, old.request_subject, old.request_body, old.replier, old.reply_summary);
            INSERT INTO tasks_fts(rowid, requester, assignee, request_subject, request_body, replier, reply_summary)
            VALUES (new.rowid, new.requester, new.assignee, new.request_subject, new.request_body, new.replier, new.reply_summary);
        END;
        """
    )
    return con


def upsert_record(con: sqlite3.Connection, record: EmailRecord) -> None:
    con.execute(
        """
        INSERT INTO emails (
            source, source_id, subject, sender, recipients, cc, email_date, body_text,
            attachment_names, filepath, category, person, gmail_thread_id, gmail_message_id,
            message_id_header, labels_json, internal_ts, snippet, body_hash, raw_sha1, indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, source_id) DO UPDATE SET
            subject=excluded.subject,
            sender=excluded.sender,
            recipients=excluded.recipients,
            cc=excluded.cc,
            email_date=excluded.email_date,
            body_text=excluded.body_text,
            attachment_names=excluded.attachment_names,
            filepath=excluded.filepath,
            category=excluded.category,
            person=excluded.person,
            gmail_thread_id=excluded.gmail_thread_id,
            gmail_message_id=excluded.gmail_message_id,
            message_id_header=excluded.message_id_header,
            labels_json=excluded.labels_json,
            internal_ts=excluded.internal_ts,
            snippet=excluded.snippet,
            body_hash=excluded.body_hash,
            raw_sha1=excluded.raw_sha1,
            indexed_at=excluded.indexed_at
        """,
        (
            record.source,
            record.source_id,
            record.subject,
            record.sender,
            record.recipients,
            record.cc,
            record.email_date,
            record.body_text,
            json.dumps(record.attachment_names, ensure_ascii=False),
            record.filepath,
            record.category,
            record.person,
            record.gmail_thread_id,
            record.gmail_message_id,
            record.message_id_header,
            record.labels_json,
            record.internal_ts,
            record.snippet,
            record.body_hash,
            record.raw_sha1,
            now_iso(),
        ),
    )
    task = extract_task_record(record)
    if task:
        con.execute(
            """
            INSERT INTO tasks (
                source, source_id, thread_key, request_date, due_date, requester, assignee,
                request_subject, request_body, status, reply_status, replier, reply_summary,
                evidence, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                thread_key=excluded.thread_key,
                request_date=excluded.request_date,
                due_date=excluded.due_date,
                requester=excluded.requester,
                assignee=excluded.assignee,
                request_subject=excluded.request_subject,
                request_body=excluded.request_body,
                status=excluded.status,
                reply_status=excluded.reply_status,
                replier=excluded.replier,
                reply_summary=excluded.reply_summary,
                evidence=excluded.evidence,
                updated_at=excluded.updated_at
            """,
            (
                task.source,
                task.source_id,
                task.thread_key,
                task.request_date,
                task.due_date,
                task.requester,
                task.assignee,
                task.request_subject,
                task.request_body,
                task.status,
                task.reply_status,
                task.replier,
                task.reply_summary,
                task.evidence,
                now_iso(),
            ),
        )
    else:
        con.execute("DELETE FROM tasks WHERE source=? AND source_id=?", (record.source, record.source_id))


def rebuild_tasks(con: sqlite3.Connection) -> int:
    rows = con.execute("SELECT * FROM emails ORDER BY internal_ts DESC, indexed_at DESC").fetchall()
    con.execute("DELETE FROM tasks")
    rebuilt = 0
    for idx, row in enumerate(rows, start=1):
        task = extract_task_record(email_record_from_row(row))
        if not task:
            continue
        con.execute(
            """
            INSERT INTO tasks (
                source, source_id, thread_key, request_date, due_date, requester, assignee,
                request_subject, request_body, status, reply_status, replier, reply_summary,
                evidence, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.source,
                task.source_id,
                task.thread_key,
                task.request_date,
                task.due_date,
                task.requester,
                task.assignee,
                task.request_subject,
                task.request_body,
                task.status,
                task.reply_status,
                task.replier,
                task.reply_summary,
                task.evidence,
                now_iso(),
            ),
        )
        rebuilt += 1
        if idx % 500 == 0:
            con.commit()
    return rebuilt


def remove_deleted_eml(con: sqlite3.Connection, existing: set[str]) -> int:
    current = {
        row["source_id"]
        for row in con.execute("SELECT source_id FROM emails WHERE source='eml'")
    }
    missing = current - existing
    for source_id in missing:
        con.execute("DELETE FROM emails WHERE source='eml' AND source_id=?", (source_id,))
    return len(missing)


def index_eml(con: sqlite3.Connection, state: dict, limit: Optional[int]) -> dict:
    eml_state = state.setdefault("eml", {})
    file_state = eml_state.setdefault("files", {})
    all_files = sorted(EMAIL_ROOT.rglob("*.eml"))
    if limit:
        all_files = all_files[:limit]
    existing_ids = {
        row["source_id"]
        for row in con.execute("SELECT source_id FROM emails WHERE source='eml'")
    }

    indexed = 0
    skipped = 0
    errors = 0
    seen_ids: set[str] = set()

    for idx, path in enumerate(all_files, start=1):
        rel = str(path.relative_to(EMAIL_ROOT)).replace("\\", "/")
        seen_ids.add(rel)
        stat = path.stat()
        signature = f"{stat.st_size}:{stat.st_mtime_ns}"
        if file_state.get(rel) == signature and rel in existing_ids:
            skipped += 1
            continue
        try:
            upsert_record(con, parse_eml(path))
            file_state[rel] = signature
            indexed += 1
            if indexed % 200 == 0:
                con.commit()
            if idx % 250 == 0:
                write_status(
                    {
                        "task": "email_search_index",
                        "stage": "eml",
                        "updatedAt": now_iso(),
                        "totalFiles": len(all_files),
                        "processed": idx,
                        "indexed": indexed,
                        "skipped": skipped,
                        "errors": errors,
                    }
                )
        except Exception as exc:
            errors += 1
            log(f"[WARN] EML parse failed: {rel}: {exc}")

    deleted = 0
    if limit is None:
        deleted = remove_deleted_eml(con, seen_ids)
    eml_state["last_scan_at"] = now_iso()
    eml_state["known_files"] = len(file_state)
    return {
        "total": len(all_files),
        "indexed": indexed,
        "skipped": skipped,
        "deleted": deleted,
        "errors": errors,
    }


def gmail_query_from_state(state: dict, fallback_days: int) -> str:
    gmail_state = state.setdefault("gmail", {})
    latest_ts = int(gmail_state.get("latest_internal_ts", 0) or 0)
    if latest_ts > 0:
        dt = datetime.fromtimestamp(max(latest_ts - 86400000, 0) / 1000, tz=timezone.utc)
        return f"in:anywhere after:{dt.strftime('%Y/%m/%d')}"
    dt = datetime.now(timezone.utc) - timedelta(days=fallback_days)
    return f"in:anywhere after:{dt.strftime('%Y/%m/%d')}"


def list_gmail_message_ids(
    session: requests.Session, query: str, max_messages: int
) -> List[str]:
    ids: List[str] = []
    page_token = None
    while len(ids) < max_messages:
        params = {
            "q": query,
            "maxResults": min(100, max_messages - len(ids)),
            "includeSpamTrash": "true",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = gmail_request(
            session,
            "GET",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params=params,
        )
        ids.extend(item["id"] for item in payload.get("messages", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return ids


def index_gmail(
    con: sqlite3.Connection,
    state: dict,
    max_messages: int,
    fallback_days: int,
    force_query: Optional[str],
) -> dict:
    session, _token = gmail_session()
    gmail_state = state.setdefault("gmail", {})
    query = force_query or gmail_query_from_state(state, fallback_days)
    ids = list_gmail_message_ids(session, query, max_messages)
    indexed = 0
    skipped = 0
    errors = 0
    latest_ts = int(gmail_state.get("latest_internal_ts", 0) or 0)

    existing_hashes = {
        row["source_id"]: row["raw_sha1"]
        for row in con.execute("SELECT source_id, raw_sha1 FROM emails WHERE source='gmail'")
    }

    for idx, message_id in enumerate(ids, start=1):
        try:
            payload = gmail_request(
                session,
                "GET",
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                params={"format": "full"},
            )
            raw_sha1 = hashlib.sha1(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8", errors="ignore")
            ).hexdigest()
            if existing_hashes.get(message_id) == raw_sha1:
                skipped += 1
                continue
            record = parse_gmail_message(payload)
            latest_ts = max(latest_ts, record.internal_ts)
            upsert_record(con, record)
            indexed += 1
            if indexed % 50 == 0:
                con.commit()
            if idx % 25 == 0:
                write_status(
                    {
                        "task": "email_search_index",
                        "stage": "gmail",
                        "updatedAt": now_iso(),
                        "query": query,
                        "totalMessages": len(ids),
                        "processed": idx,
                        "indexed": indexed,
                        "skipped": skipped,
                        "errors": errors,
                    }
                )
        except Exception as exc:
            errors += 1
            log(f"[WARN] Gmail fetch failed: {message_id}: {exc}")

    gmail_state["latest_internal_ts"] = latest_ts
    gmail_state["last_query"] = query
    gmail_state["last_scan_at"] = now_iso()
    return {
        "query": query,
        "candidates": len(ids),
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "latest_internal_ts": latest_ts,
    }


def cmd_index(args: argparse.Namespace) -> int:
    state = load_json(STATE_PATH)
    write_status({"task": "email_search_index", "stage": "starting", "updatedAt": now_iso()})
    con = connect_db()
    try:
        eml_result = index_eml(con, state, args.eml_limit)
        con.commit()
        if args.with_gmail:
            gmail_result = index_gmail(
                con,
                state,
                args.gmail_max_messages,
                args.gmail_fallback_days,
                args.gmail_force_query,
            )
            con.commit()
        else:
            gmail_result = {"skipped": True}
        rebuilt_tasks = rebuild_tasks(con)
        con.commit()
        state["updatedAt"] = now_iso()
        save_json(STATE_PATH, state)
        summary = {
            "task": "email_search_index",
            "stage": "completed",
            "updatedAt": now_iso(),
            "dbPath": str(DB_PATH),
            "eml": eml_result,
            "gmail": gmail_result,
            "taskCount": con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            "rebuiltTasks": rebuilt_tasks,
        }
        write_status(summary)
        log(json.dumps(summary, ensure_ascii=False))
        return 0
    finally:
        con.close()


def cmd_search(args: argparse.Namespace) -> int:
    con = connect_db()
    try:
        try:
            rows = con.execute(
                """
                SELECT
                    e.source,
                    e.source_id,
                    e.subject,
                    e.sender,
                    e.recipients,
                    e.email_date,
                    e.filepath,
                    e.category,
                    e.person,
                    e.snippet,
                    bm25(emails_fts) AS score
                FROM emails_fts
                JOIN emails e ON e.rowid = emails_fts.rowid
                WHERE emails_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (args.query, args.limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            terms = [term.strip() for term in re.split(r"\s+", args.query) if term.strip()]
            if not terms:
                terms = [args.query]
            clauses = []
            params: List[object] = []
            for term in terms:
                clauses.append(
                    "(subject LIKE ? OR sender LIKE ? OR recipients LIKE ? OR cc LIKE ? OR body_text LIKE ? OR attachment_names LIKE ?)"
                )
                needle = f"%{term}%"
                params.extend([needle, needle, needle, needle, needle, needle])
            params.append(args.limit)
            rows = con.execute(
                f"""
                SELECT
                    source,
                    source_id,
                    subject,
                    sender,
                    recipients,
                    email_date,
                    filepath,
                    category,
                    person,
                    snippet,
                    0.0 AS score
                FROM emails
                WHERE {' AND '.join(clauses)}
                ORDER BY internal_ts DESC, indexed_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def cmd_tasks(args: argparse.Namespace) -> int:
    con = connect_db()
    try:
        params: List[object] = []
        clauses: List[str] = []
        if args.query:
            terms = [term.strip() for term in re.split(r"\s+", args.query) if term.strip()]
            for term in terms:
                needle = f"%{term}%"
                clauses.append(
                    "(requester LIKE ? OR assignee LIKE ? OR request_subject LIKE ? OR request_body LIKE ? OR replier LIKE ? OR reply_summary LIKE ?)"
                )
                params.extend([needle, needle, needle, needle, needle, needle])
        if args.status:
            clauses.append("status = ?")
            params.append(args.status)
        if args.due_on:
            clauses.append("due_date = ?")
            params.append(args.due_on)
        params.append(args.limit)
        rows = con.execute(
            f"""
            SELECT
                source,
                source_id,
                thread_key,
                request_date,
                due_date,
                requester,
                assignee,
                request_subject,
                status,
                reply_status,
                replier,
                substr(reply_summary, 1, 280) AS reply_summary
            FROM tasks
            {'WHERE ' + ' AND '.join(clauses) if clauses else ''}
            ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date ASC, updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=cmd_search)

    tasks = sub.add_parser("tasks")
    tasks.add_argument("query", nargs="?")
    tasks.add_argument("--status")
    tasks.add_argument("--due-on")
    tasks.add_argument("--limit", type=int, default=20)
    tasks.set_defaults(func=cmd_tasks)

    parser.set_defaults(func=cmd_index)
    parser.add_argument("--without-gmail", dest="with_gmail", action="store_false")
    parser.add_argument("--gmail-max-messages", type=int, default=500)
    parser.add_argument("--gmail-fallback-days", type=int, default=365)
    parser.add_argument("--gmail-force-query")
    parser.add_argument("--eml-limit", type=int)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
