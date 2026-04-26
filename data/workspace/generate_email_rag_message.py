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
DEFAULT_LIMIT = 60
DEFAULT_URGENT_WINDOW_DAYS = 30
DEFAULT_RECENT_WINDOW_DAYS = 45
DEFAULT_STALE_DUE_DATE_DAYS = 180

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


def normalize_spaces(text: str | None) -> str:
    return " ".join((text or "").replace("\r", " ").replace("\n", " ").split())


def looks_garbled(text: str | None) -> bool:
    value = text or ""
    garbled_tokens = ["\x1b", "・ｽ", "隴", "關", "陜", "陷", "闔会"]
    return any(token in value for token in garbled_tokens)


def clean_text(value: str | None, max_len: int = 120) -> str:
    text = normalize_spaces(value)
    if not text:
        return "-"
    if looks_garbled(text):
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


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def normalize_due_date(
    due_date_value: str | None,
    request_date_value: str | None,
    today: date,
) -> tuple[date | None, str]:
    due = parse_iso_date(due_date_value)
    request_date = parse_iso_date(request_date_value)
    if not due:
        return None, "missing"

    # Some ingested tasks have impossible due dates from years before the request.
    if request_date and due < request_date - timedelta(days=7):
        return None, "invalid_before_request"

    if due < today - timedelta(days=DEFAULT_STALE_DUE_DATE_DAYS):
        return None, "stale_past"

    return due, "valid"


def due_label(due_date: date | None, due_state: str, today: date) -> str:
    if due_state == "invalid_before_request":
        return "期日データ異常"
    if due_state == "stale_past":
        return "古い期日データ"
    if not due_date:
        return "期日未設定"

    delta = (due_date - today).days
    if delta < 0:
        return f"{due_date.isoformat()} 期限切れ({abs(delta)}日)"
    if delta == 0:
        return f"{due_date.isoformat()} 本日期日"
    if delta <= 3:
        return f"{due_date.isoformat()} あと{delta}日"
    return f"{due_date.isoformat()} あと{delta}日"


def summarize_request(row: sqlite3.Row) -> str:
    subject = normalize_spaces(row["request_subject"])
    summary = normalize_spaces(row["request_summary"])
    body = normalize_spaces(row["request_body"])

    for candidate in [summary, subject, body]:
        if not candidate or looks_garbled(candidate):
            continue
        if len(candidate) > 220 and subject and not looks_garbled(subject):
            return clean_text(subject, 120)
        return clean_text(candidate, 140)

    if subject:
        return clean_text(subject, 120)
    return "[encoding issue detected]" if any(looks_garbled(v) for v in [summary, body, subject]) else "-"


def fetch_candidate_tasks(
    con: sqlite3.Connection,
    months_back: int,
    blacklist: list[str],
) -> tuple[list[dict], dict]:
    today = date.today()
    from_date = today - timedelta(days=max(months_back, 1) * 31)
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
        ORDER BY request_date DESC
        """,
        (from_date.isoformat(), today.isoformat()),
    ).fetchall()

    stats = {
        "open_recent": len(rows),
        "blacklisted": 0,
        "invalid_due": 0,
        "stale_due": 0,
        "missing_due": 0,
        "valid_due": 0,
    }

    items: list[dict] = []
    for row in rows:
        if is_blacklisted(row["request_subject"], row["requester"], blacklist):
            stats["blacklisted"] += 1
            continue

        due_date, due_state = normalize_due_date(row["due_date"], row["request_date"], today)
        if due_state == "invalid_before_request":
            stats["invalid_due"] += 1
        elif due_state == "stale_past":
            stats["stale_due"] += 1
        elif due_state == "missing":
            stats["missing_due"] += 1
        else:
            stats["valid_due"] += 1

        request_date = parse_iso_date(row["request_date"])
        if not request_date:
            continue

        items.append(
            {
                "request_date": row["request_date"] or "-",
                "request_date_obj": request_date,
                "requester": extract_requester_name(row["requester"]),
                "subject": clean_text(row["request_subject"], 90),
                "request": summarize_request(row),
                "due_date": due_date.isoformat() if due_date else "",
                "due_date_obj": due_date,
                "due_state": due_state,
                "due_label": due_label(due_date, due_state, today),
                "reply_date": row["reply_date"] or "-",
                "reply_summary": clean_text(row["reply_summary"], 100),
                "assignee": clean_text(row["assignee"], 30),
                "source": row["source"],
                "source_id": row["source_id"],
            }
        )
    return items, stats


def prioritize_tasks(items: list[dict], limit: int) -> tuple[list[dict], dict]:
    today = date.today()
    urgent_cutoff = today + timedelta(days=DEFAULT_URGENT_WINDOW_DAYS)
    recent_cutoff = today - timedelta(days=DEFAULT_RECENT_WINDOW_DAYS)

    due_soon: list[dict] = []
    overdue_recent: list[dict] = []
    recent: list[dict] = []
    backlog: list[dict] = []
    stale_due_hidden = 0

    for item in items:
        due = item["due_date_obj"]
        request_date = item["request_date_obj"]

        if item["due_state"] == "stale_past":
            stale_due_hidden += 1
            continue

        if due and today <= due <= urgent_cutoff:
            due_soon.append(item)
        elif due and due < today:
            overdue_recent.append(item)
        elif request_date >= recent_cutoff:
            recent.append(item)
        else:
            backlog.append(item)

    due_soon.sort(key=lambda item: (item["due_date_obj"], item["request_date_obj"]))
    overdue_recent.sort(
        key=lambda item: (item["request_date_obj"], item["due_date_obj"] or date.min),
        reverse=True,
    )
    recent.sort(key=lambda item: (item["request_date_obj"], item["due_date_obj"] or date.max), reverse=True)
    backlog.sort(key=lambda item: (item["request_date_obj"], item["due_date_obj"] or date.max), reverse=True)

    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for bucket in (due_soon, overdue_recent, recent, backlog):
        for item in bucket:
            key = (item["source"], item["source_id"])
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break

    stats = {
        "due_soon_candidates": len(due_soon),
        "overdue_recent_candidates": len(overdue_recent),
        "recent_candidates": len(recent),
        "backlog_candidates": len(backlog),
        "stale_due_hidden": stale_due_hidden,
        "selected": len(selected),
    }
    return selected, stats


def build_report(tasks: list[dict], months_back: int, source_stats: dict, priority_stats: dict) -> str:
    now = datetime.now(JST)
    since = now.date() - timedelta(days=max(months_back, 1) * 31)
    total_candidates = source_stats["open_recent"] - source_stats["blacklisted"]
    omitted = max(total_candidates - source_stats["stale_due"] - len(tasks), 0)

    lines = [
        "Email TodoList Report",
        "",
        f"Updated: {now.strftime('%Y-%m-%d %H:%M:%S JST')}",
        f"Range: {since.isoformat()} - {now.date().isoformat()}",
        f"Open tasks in range: {source_stats['open_recent']}",
        f"Excluded by blacklist: {source_stats['blacklisted']}",
        f"Shown: {len(tasks)}",
        f"Omitted after prioritization: {omitted}",
        "",
        "Priority rule: 期日が近い依頼を優先し、その後に直近の依頼を表示します。",
        "Invalid due dates older than the request are ignored for sorting.",
        "",
        "Fields: 依頼日 | 依頼者 | 依頼内容 | 期日 | 回答日 | 件名",
    ]

    lines.extend(
        [
            "",
            "Stats:",
            f"- valid_due={source_stats['valid_due']}",
            f"- missing_due={source_stats['missing_due']}",
            f"- invalid_due={source_stats['invalid_due']}",
            f"- stale_due_hidden={priority_stats['stale_due_hidden']}",
            f"- due_soon_candidates={priority_stats['due_soon_candidates']}",
            f"- overdue_recent_candidates={priority_stats['overdue_recent_candidates']}",
            f"- recent_candidates={priority_stats['recent_candidates']}",
            f"- backlog_candidates={priority_stats['backlog_candidates']}",
        ]
    )

    if not tasks:
        lines.extend(["", "対象となる未対応タスクはありません。"])
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
            lines.append(f"回答要約: {task['reply_summary']}")
        if task["assignee"] and task["assignee"] != "-":
            lines.append(f"担当: {task['assignee']}")
    return "\n".join(lines)


def main() -> int:
    db_path = detect_db_path()
    blacklist = load_blacklist_patterns()
    con = connect_db(db_path)
    try:
        items, source_stats = fetch_candidate_tasks(con, DEFAULT_MONTHS_BACK, blacklist)
    finally:
        con.close()

    tasks, priority_stats = prioritize_tasks(items, DEFAULT_LIMIT)
    print(build_report(tasks, DEFAULT_MONTHS_BACK, source_stats, priority_stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
