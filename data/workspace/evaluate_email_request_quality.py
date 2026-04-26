#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DB_PATH = WORKSPACE / "email_search.db"
STATUS_PATH = WORKSPACE / "email_request_quality_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def valid_due_date(due_date_value: str | None, request_date_value: str | None, today: date) -> bool:
    due = parse_iso_date(due_date_value)
    request_date = parse_iso_date(request_date_value)
    if not due:
        return False
    if request_date and due < request_date - timedelta(days=7):
        return False
    if due < today - timedelta(days=180):
        return False
    return True


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 1)


def main() -> int:
    today = date.today()
    since = today - timedelta(days=31)
    status: dict[str, Any] = {
      "startedAt": now_jst_text(),
      "dbPath": str(DB_PATH),
      "windowStart": since.isoformat(),
      "windowEnd": today.isoformat(),
      "stage": "starting",
    }
    write_status(status)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        task_rows = con.execute(
            """
            SELECT request_date, due_date, status, assignee, replier, reply_summary
            FROM tasks
            WHERE request_date <> ''
              AND request_date BETWEEN ? AND ?
            ORDER BY request_date DESC
            """,
            (since.isoformat(), today.isoformat()),
        ).fetchall()

        email_rows = con.execute(
            """
            SELECT category, sender, subject
            FROM emails
            WHERE indexed_at >= ?
            """,
            ((datetime.now(JST) - timedelta(days=31)).astimezone(timezone.utc).isoformat(),),
        ).fetchall()
    finally:
        con.close()

    status["stage"] = "evaluating"
    total_tasks = len(task_rows)
    due_detected = 0
    replied_with_detail = 0
    replied_tasks = 0
    unanswered_tasks = 0
    unassigned_open = 0
    overdue_open = 0

    for row in task_rows:
        request_date = row["request_date"]
        due_date = row["due_date"]
        if valid_due_date(due_date, request_date, today):
            due_detected += 1

        is_replied = (row["status"] or "").strip() == "replied"
        if is_replied:
            replied_tasks += 1
            if (row["replier"] or "").strip() or (row["reply_summary"] or "").strip():
                replied_with_detail += 1

        is_open = (row["status"] or "").strip() == "open"
        if is_open:
            unanswered_tasks += 1
            if not (row["assignee"] or "").strip():
                unassigned_open += 1
            due = parse_iso_date(due_date)
            if due and due < today:
                overdue_open += 1

    complaint_like = 0
    for row in email_rows:
        blob = " ".join(str(row[key] or "") for key in ("category", "sender", "subject"))
        if any(token in blob for token in ("クレーム", "不具合", "改善", "再発防止", "市場不良", "顧客不良")):
            complaint_like += 1

    metrics = {
        "task_count_31d": total_tasks,
        "deadline_detection_rate": pct(due_detected, total_tasks),
        "reply_detail_detection_rate": pct(replied_with_detail, replied_tasks),
        "open_task_rate": pct(unanswered_tasks, total_tasks),
        "unassigned_open_rate": pct(unassigned_open, unanswered_tasks),
        "overdue_open_rate": pct(overdue_open, unanswered_tasks),
        "complaint_like_email_count_31d": complaint_like,
    }
    findings: list[str] = []
    if metrics["deadline_detection_rate"] < 80.0:
        findings.append("期限抽出率が低めです。期日抽出ロジックの確認が必要です。")
    if metrics["reply_detail_detection_rate"] < 80.0 and replied_tasks > 0:
        findings.append("回答内容の抽出率が低めです。reply_summary/replier 抽出の見直し余地があります。")
    if metrics["unassigned_open_rate"] > 20.0:
        findings.append("未回答タスクに担当者未設定が多めです。")
    if metrics["overdue_open_rate"] > 20.0:
        findings.append("期限切れ未回答が多めです。優先報告の強化が必要です。")

    status["stage"] = "completed"
    status["finishedAt"] = now_jst_text()
    status["metrics"] = metrics
    status["findings"] = findings
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
