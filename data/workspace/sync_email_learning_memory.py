#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE_ROOT = SCRIPT_PATH.parent
DB_PATH = WORKSPACE_ROOT / "email_search.db"
STATUS_PATH = WORKSPACE_ROOT / "email_learning_memory_sync_status.json"
STATE_PATH = WORKSPACE_ROOT / "email_learning_memory_sync_state.json"
LEARNING_ENGINE_URL = "http://localhost:8110"
STATUS_FLUSH_INTERVAL = 25


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat()


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def maybe_write_status(payload: dict[str, Any], progress_count: int, force: bool = False) -> None:
    if force or progress_count <= 1 or progress_count % STATUS_FLUSH_INTERVAL == 0:
        write_status(payload)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(payload: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_subject(value: str | None) -> str:
    subject = normalize_space(value)
    while True:
        updated = re.sub(r"^(re|fw|fwd)\s*:\s*", "", subject, flags=re.IGNORECASE)
        if updated == subject:
            return subject
        subject = updated.strip()


def infer_thread_key(row: sqlite3.Row) -> str:
    gmail_thread_id = normalize_space(row["gmail_thread_id"])
    if gmail_thread_id:
        return f"gmail:{gmail_thread_id}"
    message_id_header = normalize_space(row["message_id_header"]).lower()
    if message_id_header:
        return message_id_header
    sender = normalize_space(row["sender"]).lower()
    subject = normalize_subject(row["subject"]).lower()
    return f"{sender}|{subject}"[:240]


def parse_json_list(value: str | None) -> list[str]:
    text = normalize_space(value)
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [normalize_space(str(item)) for item in data if normalize_space(str(item))]
    except Exception:
        pass
    return [part.strip() for part in re.split(r"[;,]", text) if part.strip()]


def parse_attachment_names(value: str | None) -> list[str]:
    text = normalize_space(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[|,;]", text) if part.strip()]


def parse_task_evidence(value: str | None) -> dict[str, Any]:
    text = normalize_space(value)
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def healthcheck(base_url: str, request_timeout: int) -> dict[str, Any]:
    resp = requests.get(f"{base_url.rstrip('/')}/health", timeout=request_timeout)
    resp.raise_for_status()
    return resp.json()


def post_json(base_url: str, route: str, payload: dict[str, Any], request_timeout: int) -> dict[str, Any]:
    resp = requests.post(f"{base_url.rstrip('/')}{route}", json=payload, timeout=request_timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_email_rows(con: sqlite3.Connection, state: dict[str, Any], bootstrap_days: int, limit: int) -> list[sqlite3.Row]:
    last_indexed_at = normalize_space(state.get("last_email_indexed_at"))
    if last_indexed_at:
        query = """
            SELECT *
            FROM emails
            WHERE indexed_at > ?
            ORDER BY indexed_at ASC, internal_ts ASC
            LIMIT ?
        """
        return con.execute(query, (last_indexed_at, limit)).fetchall()

    cutoff = (datetime.now(JST) - timedelta(days=bootstrap_days)).astimezone(timezone.utc).isoformat()
    query = """
        SELECT *
        FROM emails
        WHERE indexed_at >= ?
        ORDER BY indexed_at ASC, internal_ts ASC
        LIMIT ?
    """
    return con.execute(query, (cutoff, limit)).fetchall()


def fetch_task_rows(con: sqlite3.Connection, state: dict[str, Any], bootstrap_days: int, limit: int) -> list[sqlite3.Row]:
    last_updated_at = normalize_space(state.get("last_task_updated_at"))
    if last_updated_at:
        query = """
            SELECT *
            FROM tasks
            WHERE updated_at > ?
            ORDER BY updated_at ASC
            LIMIT ?
        """
        return con.execute(query, (last_updated_at, limit)).fetchall()

    cutoff = (datetime.now(JST) - timedelta(days=bootstrap_days)).date().isoformat()
    query = """
        SELECT *
        FROM tasks
        WHERE updated_at >= ?
        ORDER BY updated_at ASC
        LIMIT ?
        """
    return con.execute(query, (cutoff, limit)).fetchall()


def build_message_payload(row: sqlite3.Row, source_org: str) -> dict[str, Any]:
    recipients = parse_json_list(row["recipients"])
    cc = parse_json_list(row["cc"])
    attachment_names = parse_attachment_names(row["attachment_names"])
    tags = [tag for tag in [normalize_space(row["category"]), normalize_space(row["person"])] if tag]
    tags.extend(f"attachment:{name}" for name in attachment_names[:5])
    extracted_facts = [f"Attachment: {name}" for name in attachment_names[:5]]
    snippet = normalize_space(row["snippet"])
    if snippet:
        extracted_facts.append(snippet[:240])
    return {
        "message_id": f"{row['source']}:{row['source_id']}",
        "thread_id": infer_thread_key(row),
        "source_org": source_org,
        "source_type": row["source"] or "email",
        "review_status": "reviewed",
        "subject": normalize_space(row["subject"]) or "(no subject)",
        "sender": normalize_space(row["sender"]),
        "recipients": recipients + [item for item in cc if item not in recipients],
        "sent_at": normalize_space(row["email_date"]) or normalize_space(row["indexed_at"]),
        "summary": snippet or normalize_space(row["body_text"])[:600],
        "body_excerpt": normalize_space(row["body_text"])[:1200],
        "extracted_facts": extracted_facts[:8],
        "open_questions": [],
        "latest_status": normalize_space(row["category"]) or "captured",
        "tags": tags[:10],
        "extra": {
            "filepath": normalize_space(row["filepath"]),
            "gmail_thread_id": normalize_space(row["gmail_thread_id"]),
            "gmail_message_id": normalize_space(row["gmail_message_id"]),
            "labels_json": normalize_space(row["labels_json"]),
            "indexed_at": normalize_space(row["indexed_at"]),
        },
    }


def build_thread_payload(
    thread_key: str,
    tasks: list[sqlite3.Row],
    messages: list[sqlite3.Row],
    source_org: str,
) -> dict[str, Any]:
    latest_task = max(tasks, key=lambda row: normalize_space(row["updated_at"]) or "")
    participants: list[str] = []
    seen = set()
    for row in messages:
        for candidate in [normalize_space(row["sender"]), *parse_json_list(row["recipients"]), *parse_json_list(row["cc"])]:
            if candidate and candidate not in seen:
                seen.add(candidate)
                participants.append(candidate)
    open_questions = []
    next_action = ""
    latest_status = ""
    related_case_ids = []
    for task in tasks:
        if normalize_space(task["request_summary"]):
            open_questions.append(normalize_space(task["request_summary"]))
        if normalize_space(task["status"]) and not latest_status:
            latest_status = normalize_space(task["status"])
        if normalize_space(task["assignee"]) and not next_action:
            next_action = f"Follow up with {normalize_space(task['assignee'])}"
        evidence = parse_task_evidence(task["evidence"])
        if evidence.get("gmail_thread_id"):
            related_case_ids.append(str(evidence["gmail_thread_id"]))
    summary_parts = []
    if normalize_space(latest_task["request_subject"]):
        summary_parts.append(normalize_space(latest_task["request_subject"]))
    if normalize_space(latest_task["request_body"]):
        summary_parts.append(normalize_space(latest_task["request_body"])[:500])
    if normalize_space(latest_task["reply_summary"]):
        summary_parts.append(f"Reply: {normalize_space(latest_task['reply_summary'])[:300]}")
    tags = ["email_thread"]
    if latest_status:
        tags.append(f"status:{latest_status}")
    return {
        "thread_id": thread_key,
        "source_org": source_org,
        "source_type": "email_thread_rollup",
        "review_status": "reviewed",
        "subject": normalize_space(latest_task["request_subject"]) or "(thread summary)",
        "participants": participants[:20],
        "summary": " | ".join(summary_parts)[:1200],
        "open_questions": open_questions[:8],
        "latest_status": latest_status or "open",
        "next_action": next_action or "review latest thread activity",
        "related_case_ids": related_case_ids[:8],
        "tags": tags[:10],
        "extra": {
            "task_count": len(tasks),
            "message_count": len(messages),
            "latest_task_updated_at": normalize_space(latest_task["updated_at"]),
            "requester": normalize_space(latest_task["requester"]),
            "assignee": normalize_space(latest_task["assignee"]),
            "due_date": normalize_space(latest_task["due_date"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync email_search.db content into learning_engine memory")
    parser.add_argument("--base-url", default=LEARNING_ENGINE_URL)
    parser.add_argument("--source-org", default="Mitsui")
    parser.add_argument("--bootstrap-days", type=int, default=14)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--request-timeout", type=int, default=45)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    status: dict[str, Any] = {
        "startedAt": now_jst_iso(),
        "stage": "starting",
        "pid": os.getpid(),
        "baseUrl": args.base_url,
        "dbPath": str(DB_PATH),
        "dryRun": args.dry_run,
    }
    write_status(status)

    state = load_state()
    try:
        health = healthcheck(args.base_url, args.request_timeout)
        status["health"] = health
    except Exception as exc:
        status["stage"] = "skipped"
        status["reason"] = f"learning_engine unavailable: {exc}"
        status["finishedAt"] = now_jst_iso()
        write_status(status)
        return

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        email_rows = fetch_email_rows(con, state, args.bootstrap_days, args.limit)
        task_rows = fetch_task_rows(con, state, args.bootstrap_days, args.limit)
        status["stage"] = "loaded"
        status["emailCandidates"] = len(email_rows)
        status["taskCandidates"] = len(task_rows)
        status["postedMessages"] = 0
        status["postedThreads"] = 0
        status["errors"] = []
        write_status(status)

        thread_message_map: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in email_rows:
            thread_message_map[infer_thread_key(row)].append(row)

        task_thread_map: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in task_rows:
            thread_key = normalize_space(row["thread_key"])
            if thread_key:
                task_thread_map[thread_key].append(row)

        posted_messages = 0
        posted_threads = 0
        last_email_indexed_at = normalize_space(state.get("last_email_indexed_at"))
        last_task_updated_at = normalize_space(state.get("last_task_updated_at"))

        for row in email_rows:
            status["stage"] = "posting_messages"
            payload = build_message_payload(row, args.source_org)
            try:
                if not args.dry_run:
                    post_json(args.base_url, "/ingest/email-message", payload, args.request_timeout)
                posted_messages += 1
                status["postedMessages"] = posted_messages
                status["currentMessageId"] = payload["message_id"]
                maybe_write_status(status, posted_messages)
            except Exception as exc:
                status["errors"].append(
                    {
                        "stage": "message",
                        "id": payload["message_id"],
                        "detail": str(exc),
                    }
                )
                write_status(status)
            indexed_at = normalize_space(row["indexed_at"])
            if indexed_at and indexed_at > last_email_indexed_at:
                last_email_indexed_at = indexed_at

        thread_keys = sorted(set(task_thread_map) | set(thread_message_map))
        for thread_key in thread_keys:
            status["stage"] = "posting_threads"
            tasks = task_thread_map.get(thread_key, [])
            if not tasks:
                continue
            payload = build_thread_payload(
                thread_key=thread_key,
                tasks=tasks,
                messages=thread_message_map.get(thread_key, []),
                source_org=args.source_org,
            )
            try:
                if not args.dry_run:
                    post_json(args.base_url, "/ingest/email-thread", payload, args.request_timeout)
                posted_threads += 1
                status["postedThreads"] = posted_threads
                status["currentThreadId"] = payload["thread_id"]
                maybe_write_status(status, posted_threads)
            except Exception as exc:
                status["errors"].append(
                    {
                        "stage": "thread",
                        "id": payload["thread_id"],
                        "detail": str(exc),
                    }
                )
                write_status(status)
                continue
            latest_updated = max(normalize_space(task["updated_at"]) for task in tasks)
            if latest_updated and latest_updated > last_task_updated_at:
                last_task_updated_at = latest_updated

        new_state = {
            "last_email_indexed_at": last_email_indexed_at,
            "last_task_updated_at": last_task_updated_at,
            "lastRunAt": now_jst_iso(),
            "lastPostedMessages": posted_messages,
            "lastPostedThreads": posted_threads,
        }
        if not args.dry_run:
            save_state(new_state)

        status["stage"] = "completed"
        status["postedMessages"] = posted_messages
        status["postedThreads"] = posted_threads
        status["state"] = new_state
        status["finishedAt"] = now_jst_iso()
        write_status(status)
    finally:
        con.close()


if __name__ == "__main__":
    main()
