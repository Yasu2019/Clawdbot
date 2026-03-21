#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
# Filters are managed in data/workspace/email_rag_sender_filters.json.
DEFAULT_NEWSLETTER_PATTERNS = [
    "メルマガ",
    "ニュースレター",
    "配信停止",
    "配信解除",
    "unsubscribe",
    "unsub",
    "promotion",
    "キャンペーン",
    "クーポン",
    "セール",
    "お得情報",
    "premium club",
    "特集",
]
DEFAULT_BLACKLIST_PATTERNS = [
    "autodesk",
    "docusign",
    "chatwork",
    "a-thanks.net",
    "引越し侍",
    "samurai engineer",
    "sejuku.net",
    "soundhouse",
    "seshop",
    "翔泳社",
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
    "ビジネスコンシェルジュ",
    "ollama",
    "hello@ollama.com",
    "pinterest",
]


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


def load_filters() -> tuple[list[str], list[str]]:
    path = detect_filter_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            newsletter = payload.get("newsletter_patterns") or DEFAULT_NEWSLETTER_PATTERNS
            blacklist = payload.get("blacklist_patterns") or DEFAULT_BLACKLIST_PATTERNS
            return [str(v).lower() for v in newsletter], [str(v).lower() for v in blacklist]
        except Exception:
            pass
    return DEFAULT_NEWSLETTER_PATTERNS, DEFAULT_BLACKLIST_PATTERNS


NEWSLETTER_PATTERNS, BLACKLIST_PATTERNS = load_filters()


def latest_index_payload() -> dict:
    log_path = Path("/home/node/clawd/email_search_index.log")
    if not log_path.exists():
        return {}
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {}


def is_business_row(row: sqlite3.Row) -> bool:
    sender = (row["sender"] or "").lower()
    recipients = (row["recipients"] or "").lower()
    cc = (row["cc"] or "").lower()
    subject = (row["subject"] or "").lower()
    snippet = (row["snippet"] or "").lower()
    address_blob = " ".join([sender, recipients, cc])
    if "@mitsui-s" not in address_blob:
        return False
    text_blob = " ".join([sender, subject, snippet])
    if any(pattern in text_blob for pattern in NEWSLETTER_PATTERNS):
        return False
    if any(pattern in text_blob for pattern in BLACKLIST_PATTERNS):
        return False
    return True


def recent_emails(con: sqlite3.Connection, since_ts_ms: int, limit: int = 10) -> list[str]:
    rows = con.execute(
        """
        SELECT sender, recipients, cc, subject, snippet, internal_ts
        FROM emails
        WHERE COALESCE(subject, '') <> 'Email RAG Ingest'
          AND COALESCE(sender, '') NOT LIKE '%y.suzuki.hk@gmail.com%'
          AND COALESCE(internal_ts, 0) >= ?
        ORDER BY internal_ts DESC, indexed_at DESC
        """,
        (since_ts_ms,),
    ).fetchall()
    lines: list[str] = []
    for row in rows:
        if not is_business_row(row):
            continue
        sender = (row["sender"] or "-").replace("\n", " ").strip()
        subject = (row["subject"] or "-").replace("\n", " ").strip()
        snippet = " ".join((row["snippet"] or "").replace("\r", " ").replace("\n", " ").split())
        if len(snippet) > 70:
            snippet = snippet[:67] + "..."
        ts = row["internal_ts"]
        at = datetime.fromtimestamp(ts / 1000, JST).strftime("%Y-%m-%d %H:%M") if ts else "-"
        lines.append(f"{len(lines) + 1}. [{at}] {sender} / {subject}\n   {snippet or '-'}")
        if len(lines) >= limit:
            break
    return lines


def weekly_stats(con: sqlite3.Connection, since_ts_ms: int) -> dict:
    rows = con.execute(
        """
        SELECT sender, recipients, cc, subject, snippet
        FROM emails
        WHERE COALESCE(subject, '') <> 'Email RAG Ingest'
          AND COALESCE(sender, '') NOT LIKE '%y.suzuki.hk@gmail.com%'
          AND COALESCE(internal_ts, 0) >= ?
        """,
        (since_ts_ms,),
    ).fetchall()
    filtered = [row for row in rows if is_business_row(row)]
    return {
        "emailCount": len(filtered),
        "senderCount": len({(row["sender"] or "").strip() for row in filtered}),
    }


def main() -> int:
    payload = latest_index_payload()
    gmail = payload.get("gmail") or {}
    eml = payload.get("eml") or {}
    now = datetime.now(JST)
    since = now - timedelta(days=7)
    since_ts_ms = int(since.timestamp() * 1000)
    db_path = detect_db_path()
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        stats = weekly_stats(con, since_ts_ms)
        recent_lines = recent_emails(con, since_ts_ms, limit=10)
    finally:
        con.close()

    lines = [
        "メール取込完了",
        "",
        f"更新時刻: {payload.get('updatedAt', '(unknown)')}",
        f"Gmail候補: {gmail.get('candidates', 0)} 件",
        f"Gmail取込: {gmail.get('indexed', 0)} 件",
        f"Gmailスキップ: {gmail.get('skipped', 0)} 件",
        f"EML総数: {eml.get('total', 0)} 件",
        f"タスク件数: {payload.get('taskCount', '(n/a)')} 件",
        f"再構築タスク: {payload.get('rebuiltTasks', '(n/a)')} 件",
        f"通知対象期間: {since.strftime('%Y-%m-%d')} ～ {now.strftime('%Y-%m-%d')}",
        f"過去1週間の業務メール件数: {stats['emailCount']} 件",
        f"過去1週間の業務送信者数: {stats['senderCount']} 件",
    ]
    if gmail.get("query"):
        lines.append(f"対象クエリ: {gmail['query']}")
    lines.extend(["", "過去1週間の業務メール抜粋:"])
    if recent_lines:
        lines.extend(recent_lines)
    else:
        lines.append("過去1週間の対象メールは見つかりませんでした。")
    lines.extend(
        [
            "",
            "Qdrant: nightly stable mode ではスキップ",
            "Meilisearch: nightly stable mode ではスキップ",
        ]
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
