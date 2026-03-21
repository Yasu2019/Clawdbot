#!/usr/bin/env python3
"""
email_search_query.py

Host/container-safe query helper for email_search.db.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from functools import lru_cache
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional


COMMON_TERMS = {
    "mail", "gmail", "eml", "summary", "search", "email", "emails", "message", "messages",
    "メール", "要約", "検索", "件名", "本文", "送信者", "受信", "返信", "最近", "昨日", "今日",
}
TASK_TERMS = {
    "依頼", "依頼事項", "提出", "期日", "期限", "締切", "タスク", "宿題", "回答状況",
    "未回答", "未回答のみ", "回答者", "回答内容", "回答内容つき", "依頼者", "担当者", "今週", "今週期限",
    "今月", "今月期限", "期限切れ", "期限切れ未回答のみ", "のみ", "つき",
    "todo", "task", "tasks", "deadline", "due", "open",
}
RELATIVE_TERMS = {
    "昨日", "今日", "明日", "本日", "先週", "先月", "今週", "今月",
    "recent", "yesterday", "today", "tomorrow", "lastweek", "lastmonth", "thisweek", "thismonth",
}


WORKSPACE = Path(__file__).resolve().parent
MITSUI_GLOSSARY_PATHS = (
    WORKSPACE / "mitsui_terms.md",
    WORKSPACE / "mitsui_terms_auto.md",
    WORKSPACE.parent.parent / "ミツイ精密専門用語",
)


@lru_cache(maxsize=1)
def load_mitsui_glossary_terms() -> List[str]:
    terms: set[str] = set()
    for path in MITSUI_GLOSSARY_PATHS:
        try:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
                continue
            stripped = re.sub(r"^\d+\.\s*", "", stripped)
            stripped = re.sub(r"^[\-*\u30fb]+\s*", "", stripped)
            if ":" in stripped:
                _, stripped = stripped.split(":", 1)
            for part in re.split(r"[,、/\|]", stripped):
                candidate = re.sub(r"\s+", " ", part).strip()
                candidate = re.sub(r"^\d+\.\s*", "", candidate)
                candidate = candidate.strip("()[]{}<>\"'")
                if len(candidate) < 2:
                    continue
                if candidate.lower() in {"manual terms", "auto terms", "mitsui terms", "mitsui terms auto"}:
                    continue
                terms.add(candidate)
    return sorted(terms, key=lambda item: (-len(item), item))


def expand_with_mitsui_glossary(terms: List[str], max_expansions: int = 12) -> List[str]:
    if not terms:
        return terms
    glossary = load_mitsui_glossary_terms()
    if not glossary:
        return terms

    expanded: List[str] = []
    seen: set[str] = set()

    def add_term(value: str) -> None:
        normalized = value.strip()
        if not normalized:
            return
        key = normalized.casefold()
        if key in seen:
            return
        seen.add(key)
        expanded.append(normalized)

    for term in terms:
        add_term(term)

    added = 0
    for term in terms:
        term_fold = term.casefold()
        compact = re.sub(r"[\s\-_/]", "", term_fold)
        for glossary_term in glossary:
            glossary_fold = glossary_term.casefold()
            glossary_compact = re.sub(r"[\s\-_/]", "", glossary_fold)
            matched = (
                term_fold == glossary_fold
                or term_fold in glossary_fold
                or glossary_fold in term_fold
                or (compact and compact == glossary_compact)
                or (compact and compact in glossary_compact and len(compact) >= 3)
            )
            if not matched:
                continue
            before_len = len(expanded)
            add_term(glossary_term)
            if len(expanded) > before_len:
                added += 1
                if added >= max_expansions:
                    return expanded
    return expanded


def detect_db_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    candidates = [
        Path(__file__).resolve().parent / "email_search.db",
        Path("/home/node/clawd/email_search.db"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def connect_db(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def tokenize_query(query: str) -> List[str]:
    raw_terms = [term.strip() for term in re.split(r"\s+", query or "") if term.strip()]
    terms: List[str] = []
    for raw in raw_terms:
        cleaned = re.sub(r"[\"'、。,.!?:;()\[\]{}]+", "", raw)
        if not cleaned:
            continue
        if cleaned.lower() in COMMON_TERMS or cleaned.lower() in TASK_TERMS:
            continue
        if cleaned in COMMON_TERMS or cleaned in TASK_TERMS:
            continue
        terms.append(cleaned)
    return terms


def tokenize_task_query(query: str) -> List[str]:
    cleaned_query = query or ""
    cleaned_query = re.sub(r"依頼者[=:：は]?\s*[^\s、。]+", " ", cleaned_query)
    cleaned_query = re.sub(r"回答者[=:：は]?\s*[^\s、。]+", " ", cleaned_query)
    cleaned_query = re.sub(r"担当者[=:：は]?\s*[^\s、。]+", " ", cleaned_query)
    for token in (
        "期限切れ未回答のみ", "未回答のみ", "未回答", "未返信", "未処理",
        "回答済", "返信済", "対応済", "今週期限", "今週", "今月期限", "今月",
        "期限切れ", "回答内容つき", "回答内容", "依頼事項", "依頼", "担当者",
        "依頼者", "回答者", "期限", "期日", "締切", "のみ", "つき",
    ):
        cleaned_query = cleaned_query.replace(token, " ")
    terms = tokenize_query(cleaned_query)
    filtered: List[str] = []
    for term in terms:
        normalized = re.sub(r"[年月日/.\-]", "", term)
        if re.fullmatch(r"\d{1,8}", normalized):
            continue
        if len(normalized) <= 1:
            continue
        if "から" in term or "まで" in term:
            continue
        if term in {"の", "まで", "から", "が", "は"}:
            continue
        filtered.append(term)
    return filtered


def relative_requested(query: str) -> bool:
    compact = re.sub(r"\s+", "", (query or "").lower())
    return any(term in compact for term in RELATIVE_TERMS)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[dict]:
    return [dict(row) for row in rows]


def search_rows(con: sqlite3.Connection, query: str, limit: int) -> List[sqlite3.Row]:
    rows: List[sqlite3.Row] = []
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
                bm25(emails_fts) AS score,
                e.internal_ts
            FROM emails_fts
            JOIN emails e ON e.rowid = emails_fts.rowid
            WHERE emails_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if rows:
        return rows

    terms = tokenize_query(query)
    if not terms and query.strip():
        terms = [query.strip()]
    if not terms:
        return []

    clauses = []
    params: List[object] = []
    for term in terms:
        clauses.append(
            "(subject LIKE ? OR sender LIKE ? OR recipients LIKE ? OR cc LIKE ? OR body_text LIKE ? OR attachment_names LIKE ?)"
        )
        needle = f"%{term}%"
        params.extend([needle, needle, needle, needle, needle, needle])
    params.append(limit)
    return con.execute(
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
            0.0 AS score,
            internal_ts
        FROM emails
        WHERE {' AND '.join(clauses)}
        ORDER BY internal_ts DESC, indexed_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def recent_rows(con: sqlite3.Connection, limit: int) -> List[sqlite3.Row]:
    return con.execute(
        """
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
            0.0 AS score,
            internal_ts
        FROM emails
        ORDER BY internal_ts DESC, indexed_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def dedupe(rows: Iterable[sqlite3.Row]) -> List[dict]:
    seen = set()
    output: List[dict] = []
    for row in rows:
        item = dict(row)
        key = (item.get("source"), item.get("source_id"))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def build_context(query: str, rows: List[dict], fallback_kind: str) -> str:
    if not rows:
        return ""
    heading = "Relevant local email records"
    if fallback_kind == "recent":
        heading = "Recent local email records"
    lines = [
        f"{heading} for: {query}",
        "Use only if they are relevant. If the context is insufficient, say so.",
    ]
    for idx, row in enumerate(rows, start=1):
        date_text = row.get("email_date") or "unknown-date"
        source = row.get("source") or "email"
        subject = (row.get("subject") or "").replace("\n", " ").strip()
        sender = (row.get("sender") or "").replace("\n", " ").strip()
        snippet = re.sub(r"\s+", " ", row.get("snippet") or "").strip()
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        lines.append(f"[{idx}] {date_text} | {source} | from={sender} | subject={subject}\n{snippet}")
    return "\n\n".join(lines)


def build_email_summary(query: str, rows: List[dict], fallback_kind: str) -> str:
    if not rows:
        return "該当するメールは見つかりませんでした。"
    header = f"関連メールを {len(rows)} 件確認しました。"
    if fallback_kind == "recent":
        header = f"直近メールを {len(rows)} 件確認しました。"
    lines = [header]
    for idx, row in enumerate(rows[:5], start=1):
        date_text = row.get("email_date") or "-"
        sender = (row.get("sender") or "-").replace("\n", " ").strip()
        subject = (row.get("subject") or "-").replace("\n", " ").strip()
        lines.append(f"{idx}. {date_text} / {sender} / {subject}")
    return "\n".join(lines)


def parse_specific_date(query: str) -> Optional[date]:
    compact = re.sub(r"\s+", "", query or "")
    match = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", compact)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", compact)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def parse_explicit_date_range(query: str) -> tuple[Optional[date], Optional[date]]:
    compact = re.sub(r"\s+", "", query or "")
    today = datetime.now().date()

    match = re.search(
        r"(?:(20\d{2})[/-])?(\d{1,2})[/-](\d{1,2})から(?:(20\d{2})[/-])?(\d{1,2})[/-](\d{1,2})(?:まで)?",
        compact,
    )
    if match:
        start_year = int(match.group(1) or today.year)
        start_month = int(match.group(2))
        start_day = int(match.group(3))
        end_year = int(match.group(4) or start_year)
        end_month = int(match.group(5))
        end_day = int(match.group(6))
        return date(start_year, start_month, start_day), date(end_year, end_month, end_day)

    match = re.search(
        r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日から(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日(?:まで)?",
        compact,
    )
    if match:
        start_year = int(match.group(1) or today.year)
        start_month = int(match.group(2))
        start_day = int(match.group(3))
        end_year = int(match.group(4) or start_year)
        end_month = int(match.group(5))
        end_day = int(match.group(6))
        return date(start_year, start_month, start_day), date(end_year, end_month, end_day)

    match = re.search(
        r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日から(\d{1,2})日(?:まで)?",
        compact,
    )
    if match:
        year = int(match.group(1) or today.year)
        month = int(match.group(2))
        start_day = int(match.group(3))
        end_day = int(match.group(4))
        return date(year, month, start_day), date(year, month, end_day)

    match = re.search(
        r"(?:(20\d{2})年)?(\d{1,2})月1日から末日(?:まで)?",
        compact,
    )
    if match:
        year = int(match.group(1) or today.year)
        month = int(match.group(2))
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return start, end

    return None, None


def resolve_due_range(query: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    today = datetime.now().date()
    compact = re.sub(r"\s+", "", query or "")
    range_start, range_end = parse_explicit_date_range(query)
    if range_start and range_end:
        return None, range_start.isoformat(), range_end.isoformat()
    exact = parse_specific_date(query)
    if exact:
        exact_str = exact.isoformat()
        return exact_str, exact_str, exact_str
    lower = compact.lower()
    if "明日" in compact or "tomorrow" in lower:
        exact_str = (today + timedelta(days=1)).isoformat()
        return exact_str, exact_str, exact_str
    if "今日" in compact or "本日" in compact or "today" in lower:
        exact_str = today.isoformat()
        return exact_str, exact_str, exact_str
    if "昨日" in compact or "yesterday" in lower:
        exact_str = (today - timedelta(days=1)).isoformat()
        return exact_str, exact_str, exact_str
    if "今週" in compact:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return None, start.isoformat(), end.isoformat()
    if "今月" in compact:
        start = today.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        return None, start.isoformat(), end.isoformat()
    return None, None, None


def extract_named_filter(query: str, label: str) -> str:
    escaped = re.escape(label)
    patterns = [
        rf"{escaped}[=:：は]?\s*([^\s、。]+)",
        rf"{escaped}\s+([^\s、。]+)",
        rf"([^\s、。]+)\s*{escaped}",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return match.group(1).strip()
    return ""


def extract_requester_filter(query: str) -> str:
    patterns = [
        r"依頼者[=:：]?\s*([^\s、。,．]+)",
        r"依頼者\s+([^\s、。,．]+)",
        r"from\s+([^\s、。,．]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_assignee_filter(query: str) -> str:
    patterns = [
        r"担当者[=:：]?\s*([^\s、。,．]+)",
        r"担当者\s+([^\s、。,．]+)",
        r"assignee[=:：]?\s*([^\s、。,．]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_replier_filter(query: str) -> str:
    patterns = [
        r"回答者[=:：]?\s*([^\s、。,．]+)",
        r"回答者\s+([^\s、。,．]+)",
        r"replier[=:：]?\s*([^\s、。,．]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def wants_unanswered_only(query: str) -> bool:
    compact = re.sub(r"\s+", "", query or "")
    lower = compact.lower()
    return any(token in compact for token in ("未回答のみ", "未回答", "未返信", "未処理", "期限切れ未回答のみ")) or "unanswered" in lower or "open" in lower


def wants_replied_only(query: str) -> bool:
    compact = re.sub(r"\s+", "", query or "")
    lower = compact.lower()
    return any(token in compact for token in ("回答済", "返信済", "対応済")) or "replied" in lower


def wants_overdue(query: str) -> bool:
    compact = re.sub(r"\s+", "", query or "")
    lower = compact.lower()
    return "期限切れ" in compact or "overdue" in lower


def task_rows(con: sqlite3.Connection, query: str, limit: int) -> List[sqlite3.Row]:
    clauses: List[str] = []
    params: List[object] = []

    due_on, due_from, due_to = resolve_due_range(query)
    if due_on:
        clauses.append("due_date = ?")
        params.append(due_on)
    elif due_from and due_to:
        clauses.append("due_date BETWEEN ? AND ?")
        params.extend([due_from, due_to])

    if wants_overdue(query):
        clauses.append("due_date <> '' AND due_date < date('now','localtime')")

    if wants_unanswered_only(query):
        clauses.append("status = 'open'")
    elif wants_replied_only(query):
        clauses.append("status = 'replied'")

    requester = extract_requester_filter(query)
    if requester:
        needle = f"%{requester}%"
        clauses.append("(requester LIKE ? OR request_subject LIKE ? OR request_body LIKE ?)")
        params.extend([needle, needle, needle])

    assignee = extract_assignee_filter(query)
    if assignee:
        needle = f"%{assignee}%"
        clauses.append("(assignee LIKE ? OR request_subject LIKE ? OR request_body LIKE ?)")
        params.extend([needle, needle, needle])

    replier = extract_replier_filter(query)
    if replier:
        needle = f"%{replier}%"
        clauses.append("(replier LIKE ? OR reply_summary LIKE ? OR request_body LIKE ?)")
        params.extend([needle, needle, needle])

    terms = tokenize_task_query(query)
    for term in terms:
        needle = f"%{term}%"
        clauses.append(
            "(requester LIKE ? OR assignee LIKE ? OR request_subject LIKE ? OR request_body LIKE ? OR replier LIKE ? OR reply_summary LIKE ?)"
        )
        params.extend([needle, needle, needle, needle, needle, needle])

    params.append(limit)
    return con.execute(
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
            request_body,
            status,
            reply_status,
            replier,
            reply_summary
        FROM tasks
        {'WHERE ' + ' AND '.join(clauses) if clauses else ''}
        ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date ASC, request_date DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def is_garbled_text(value: str) -> bool:
    if not value:
        return False
    if "\x1b" in value:
        return True
    suspicious = ("\u001b", "�", "縺", "繧", "荳", "譛")
    return sum(1 for token in suspicious if token in value) >= 2


def clean_display_text(value: str, max_len: int = 80) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if not text:
        return "-"
    if is_garbled_text(text):
        return "[文字化けのため省略]"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def format_status_label(status: str) -> str:
    mapping = {
        "open": "未回答",
        "replied": "回答済",
        "unknown": "不明",
    }
    return mapping.get((status or "").strip(), status or "-")


def build_task_context(query: str, rows: List[dict]) -> str:
    if not rows:
        return ""
    lines = [
        f"Relevant local task records for: {query}",
        "Prioritize these structured task records over raw email snippets.",
    ]
    for idx, row in enumerate(rows, start=1):
        request_body = clean_display_text(row.get("request_body") or "", 220)
        reply_summary = clean_display_text(row.get("reply_summary") or "", 160)
        lines.append(
            f"[{idx}] due={row.get('due_date') or '-'} status={row.get('status') or '-'} "
            f"requester={row.get('requester') or '-'} assignee={row.get('assignee') or '-'} "
            f"replier={row.get('replier') or '-'} subject={row.get('request_subject') or '-'}"
        )
        if request_body != "-":
            lines.append(f"request: {request_body}")
        if reply_summary != "-":
            lines.append(f"reply: {reply_summary}")
    return "\n".join(lines)


def build_task_summary(query: str, rows: List[dict]) -> str:
    due_on, due_from, due_to = resolve_due_range(query)
    requester = extract_requester_filter(query)
    assignee = extract_assignee_filter(query)
    replier = extract_replier_filter(query)
    unanswered = wants_unanswered_only(query)
    replied = wants_replied_only(query)
    overdue = wants_overdue(query)
    wants_reply_detail = any(token in query for token in ("回答者", "回答内容", "返信内容"))

    if not rows:
        scope = "該当する依頼事項"
        if due_on:
            scope = f"{due_on} が期限の依頼事項"
        elif due_from and due_to:
            scope = f"{due_from} から {due_to} が期限の依頼事項"
        if requester:
            scope += f"（依頼者: {requester}）"
        if assignee:
            scope += f"（担当者: {assignee}）"
        if replier:
            scope += f"（回答者: {replier}）"
        if overdue:
            scope += " の期限切れ分"
        if unanswered:
            scope += " の未回答分"
        return f"{scope} は見つかりませんでした。"

    header_scope = "該当する依頼事項"
    if due_on:
        header_scope = f"{due_on} が期限の依頼事項"
    elif due_from and due_to:
        header_scope = f"{due_from} から {due_to} が期限の依頼事項"
    if requester:
        header_scope += f"（依頼者: {requester}）"
    if assignee:
        header_scope += f"（担当者: {assignee}）"
    if replier:
        header_scope += f"（回答者: {replier}）"
    if overdue:
        header_scope += " の期限切れ分"
    if unanswered:
        header_scope += " の未回答分"
    elif replied:
        header_scope += " の回答済分"

    lines = [f"{header_scope}\n{len(rows)} 件あります。"]
    for idx, row in enumerate(rows[:5], start=1):
        due_date = row.get("due_date") or "-"
        subject = clean_display_text(row.get("request_subject") or "-", 72)
        requester_text = clean_display_text(row.get("requester") or "-", 28)
        assignee_text = clean_display_text(row.get("assignee") or "-", 20)
        status = format_status_label(row.get("status") or "-")
        parts = [
            f"{idx}. {subject}",
            f"期限: {due_date}",
            f"状態: {status}",
            f"依頼者: {requester_text}",
            f"担当: {assignee_text}",
        ]
        if wants_reply_detail:
            replier_text = clean_display_text(row.get("replier") or "-", 24)
            reply_summary = clean_display_text(row.get("reply_summary") or "", 80)
            parts.append(f"回答者: {replier_text}")
            if reply_summary != "-":
                parts.append(f"回答内容: {reply_summary}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def cmd_search(args: argparse.Namespace) -> int:
    con = connect_db(detect_db_path(args.db))
    try:
        rows = rows_to_dicts(search_rows(con, args.query, args.limit))
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def cmd_context(args: argparse.Namespace) -> int:
    con = connect_db(detect_db_path(args.db))
    try:
        primary = dedupe(search_rows(con, args.query, args.limit))
        fallback_kind = "search"
        if (not primary and relative_requested(args.query)) or args.recent_only:
            primary = dedupe(recent_rows(con, args.limit))
            fallback_kind = "recent"
        payload = {
            "query": args.query,
            "db_path": str(detect_db_path(args.db)),
            "result_count": len(primary),
            "fallback_kind": fallback_kind,
            "results": primary,
            "summary": build_email_summary(args.query, primary, fallback_kind),
            "context": build_context(args.query, primary, fallback_kind),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def cmd_tasks(args: argparse.Namespace) -> int:
    con = connect_db(detect_db_path(args.db))
    try:
        rows = rows_to_dicts(task_rows(con, args.query, args.limit))
        due_on, due_from, due_to = resolve_due_range(args.query)
        payload = {
            "query": args.query,
            "db_path": str(detect_db_path(args.db)),
            "result_count": len(rows),
            "results": rows,
            "summary": build_task_summary(args.query, rows),
            "context": build_task_context(args.query, rows),
            "due_on": due_on,
            "due_from": due_from,
            "due_to": due_to,
            "requester": extract_requester_filter(args.query),
            "assignee": extract_assignee_filter(args.query),
            "replier": extract_replier_filter(args.query),
            "unanswered_only": wants_unanswered_only(args.query),
            "overdue_only": wants_overdue(args.query),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.set_defaults(func=cmd_search)

    context = sub.add_parser("context")
    context.add_argument("query")
    context.add_argument("--limit", type=int, default=5)
    context.add_argument("--recent-only", action="store_true")
    context.set_defaults(func=cmd_context)

    tasks = sub.add_parser("tasks-context")
    tasks.add_argument("query")
    tasks.add_argument("--limit", type=int, default=5)
    tasks.set_defaults(func=cmd_tasks)

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
