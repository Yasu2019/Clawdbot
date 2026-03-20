#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path


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


def clean_text(value: str | None, max_len: int = 80) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return "-"
    if "\x1b" in text:
        return "[文字化けのため省略]"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def build_summary(rows: list[sqlite3.Row], from_date: str, to_date: str, limit: int) -> str:
    lines = [
        f"ToDo定刻レポート（対象: {from_date} ～ {to_date}）",
        f"直近6か月の未対応案件: {len(rows)}件 / 表示: {min(len(rows), limit)}件",
    ]
    if not rows:
        lines.append("直近6か月では未対応案件は見つかりませんでした。")
        lines.append("さらに古い案件を見たい場合は、months_back を増やして再生成します。")
        return "\n".join(lines)

    for idx, row in enumerate(rows[:limit], start=1):
        lines.append("")
        lines.append(f"{idx}. {clean_text(row['request_subject'], 72)}")
        lines.append(f"依頼日: {row['request_date'] or '-'} / 期限: {row['due_date'] or '-'}")
        lines.append(f"依頼者: {clean_text(row['requester'], 30)} / 担当: {clean_text(row['assignee'], 20)}")
        lines.append(f"内容: {clean_text(row['request_body'], 90)}")
    lines.append("")
    lines.append("さらに過去へさかのぼりたい場合は、months_back を増やして再送できます。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--months-back", type=int, default=6)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    db_path = detect_db_path(args.db)
    to_date = date.today()
    from_date = to_date - timedelta(days=max(args.months_back, 1) * 31)

    con = connect_db(db_path)
    try:
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
                reply_summary
            FROM tasks
            WHERE status = 'open'
              AND request_date <> ''
              AND request_date BETWEEN ? AND ?
            ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date ASC, request_date DESC
            LIMIT ?
            """,
            (from_date.isoformat(), to_date.isoformat(), args.limit),
        ).fetchall()
        payload = {
            "db_path": str(db_path),
            "months_back": args.months_back,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "result_count": len(rows),
            "results": [dict(row) for row in rows],
            "summary": build_summary(rows, from_date.isoformat(), to_date.isoformat(), args.limit),
            "rule": "定刻送信の既定範囲は直近6か月です。さらに過去を希望した場合は months_back を増やして再送します。",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
