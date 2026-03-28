#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
DEFAULT_MONTHS_BACK = 6
DEFAULT_LIMIT = 20

DEFAULT_BLACKLIST_PATTERNS = [
    "autodesk",
    "docusign",
    "chatwork",
    "a-thanks.net",
    "samurai engineer",
    "sejuku.net",
    "soundhouse",
    "seshop",
    "hmv",
    "morecos",
    "point.recruit.co.jp",
    "recruit",
    "epark",
    "audiobook.jp",
    "netflix",
    "job-medley.com",
    "job-medley",
    "mitsui.seimitsu.iatf16949@gmail.com",
    "isrg",
    "abetterinternet.org",
    "udemy",
    "students.udemy.com",
    "onamae.com",
    "ollama",
    "hello@ollama.com",
    "pinterest",
]


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def detect_db_path() -> Path:
    candidates = [
        Path("/home/node/clawd/email_search.db"),
        Path(__file__).resolve().parent / "email_search.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def detect_filter_path() -> Path:
    candidates = [
        Path("/home/node/clawd/email_rag_sender_filters.json"),
        Path(__file__).resolve().parent / "email_rag_sender_filters.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def load_blacklist_patterns() -> list[str]:
    path = detect_filter_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            values = payload.get("blacklist_patterns") or DEFAULT_BLACKLIST_PATTERNS
            return [str(v).lower() for v in values if str(v).strip()]
        except Exception:
            pass
    return DEFAULT_BLACKLIST_PATTERNS


def connect_db(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def clean_text(value: str | None, max_len: int = 120) -> str:
    text = " ".join((value or "").replace("\r", " ").replace("\n", " ").split())
    if not text:
        return "-"
    if "\x1b" in text:
        return "[encoding issue detected]"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def extract_requester_name(requester: str | None) -> str:
    text = (requester or "").strip()
    if not text:
        return "-"
    match = re.match(r'^"?([^"<]+)"?\s*<[^>]+>', text)
    if match:
        return clean_text(match.group(1), 40)
    return clean_text(text, 40)


def is_blacklisted(subject: str | None, requester: str | None, blacklist: list[str]) -> bool:
    target = ((subject or "") + " " + (requester or "")).lower()
    return any(pattern in target for pattern in blacklist)


def due_label(due_date: str) -> str:
    if not due_date:
        return "未設定"
    try:
        due = date.fromisoformat(due_date)
        delta = (due - date.today()).days
        if delta < 0:
            return f"{due_date} 🔴期限切れ({abs(delta)}日)"
        if delta == 0:
            return f"{due_date} 🟠今日"
        if delta <= 3:
            return f"{due_date} 🟡{delta}日"
        return f"{due_date} {delta}日"
    except ValueError:
        return due_date


def fetch_open_tasks(con: sqlite3.Connection, months_back: int, limit: int, blacklist: list[str]) -> list[dict]:
    to_date = date.today()
    from_date = to_date - timedelta(days=max(months_back, 1) * 31)
    rows = con.execute(
        """
        SELECT
            source,
            source_id,
            request_date,
            due_date,
            requester,
            assignee,
            request_subject,
            request_body,
            status,
            reply_status,
            replier,
            reply_summary,
            reply_date,
            request_summary
        FROM tasks
        WHERE status = 'open'
          AND request_date <> ''
          AND request_date BETWEEN ? AND ?
        ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date ASC, request_date DESC
        """,
        (from_date.isoformat(), to_date.isoformat()),
    ).fetchall()

    items: list[dict] = []
    for row in rows:
        if is_blacklisted(row["request_subject"], row["requester"], blacklist):
            continue
        requester = extract_requester_name(row["requester"])
        request_text = row["request_summary"] or row["request_body"] or row["request_subject"]
        items.append(
            {
                "request_date": row["request_date"] or "-",
                "requester": requester,
                "subject": clean_text(row["request_subject"], 90),
                "request": clean_text(request_text, 140),
                "due_date": row["due_date"] or "",
                "due_label": due_label(row["due_date"] or ""),
                "reply_date": row["reply_date"] or "-",
                "reply_summary": clean_text(row["reply_summary"], 100),
                "assignee": clean_text(row["assignee"], 30),
                "source_id": row["source_id"],
            }
        )
        if len(items) >= limit:
            break
    return items


def build_report(tasks: list[dict], months_back: int) -> str:
    now = datetime.now(JST)
    since = now.date() - timedelta(days=max(months_back, 1) * 31)
    lines = [
        "Email TodoList Report",
        "",
        f"Updated: {now.strftime('%Y-%m-%d %H:%M:%S JST')}",
        f"Range: {since.isoformat()} - {now.date().isoformat()}",
        f"Open tasks shown: {len(tasks)}",
        "",
        "Fields: request_date | requester | request | due_date | reply_date | subject",
    ]
    if not tasks:
        lines.extend(["", "No open tasks found in the selected period."])
        return "\n".join(lines)

    for idx, task in enumerate(tasks, start=1):
        lines.extend(
            [
                "",
                "-" * 72,
                f"[{idx}]",
                f"依頼日: {task['request_date']}",
                f"依頼者: {task['requester']}",
                f"依頼内容: {task['request']}",
                f"期日: {task['due_label']}",
                f"回答日: {task['reply_date']}",
                f"件名: {task['subject']}",
            ]
        )
        if task["reply_summary"] and task["reply_summary"] != "-":
            lines.append(f"回答内容: {task['reply_summary']}")
        if task["assignee"] and task["assignee"] != "-":
            lines.append(f"担当: {task['assignee']}")
    return "\n".join(lines)


def main() -> int:
    db_path = detect_db_path()
    blacklist = load_blacklist_patterns()
    con = connect_db(db_path)
    try:
        tasks = fetch_open_tasks(con, DEFAULT_MONTHS_BACK, DEFAULT_LIMIT, blacklist)
    finally:
        con.close()
    print(build_report(tasks, DEFAULT_MONTHS_BACK))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
