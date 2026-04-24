#!/usr/bin/env python3
"""
run_attachment_text_backfill.py

Waits for the priority Gmail backfill to finish, then extracts text from
attachments (PDF/Excel/Word) for Gmail records that have attachment filenames
but no extracted content yet.

Processes in batches to avoid long DB locks. Acquires EmailDbLock before each batch.

Usage:
    python run_attachment_text_backfill.py [--batch 100] [--limit 0]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from email_db_lock import EmailDbLock, read_lock_owner

JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
STATUS_PATH = WORKSPACE / "attachment_text_backfill_status.json"
HOST_DB_PATH = WORKSPACE / "email_search.db"
BACKFILL_STATUS_PATH = WORKSPACE / "gmail_priority_backfill_status.json"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_email_search_index():
    spec = importlib.util.spec_from_file_location("email_search_index", str(WORKSPACE / "email_search_index.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def priority_backfill_finished() -> bool:
    try:
        status = json.loads(BACKFILL_STATUS_PATH.read_text(encoding="utf-8"))
        return status.get("stage") == "completed"
    except Exception:
        return True


def wait_for_priority_backfill(poll_secs: int = 30) -> None:
    if priority_backfill_finished():
        return
    print(f"[{now_jst()}] Waiting for priority Gmail backfill to complete ...", flush=True)
    while not priority_backfill_finished():
        time.sleep(poll_secs)
    print(f"[{now_jst()}] Priority backfill complete. Starting attachment text backfill.", flush=True)


def count_remaining(mod) -> int:
    con = mod.connect_db()
    try:
        return con.execute(
            """
            SELECT COUNT(*) FROM emails
            WHERE source='gmail'
              AND attachment_names NOT IN ('[]', '', 'null')
              AND (attachment_text IS NULL OR attachment_text = '')
            """
        ).fetchone()[0]
    finally:
        con.close()


def run_batch(mod, batch_size: int) -> dict:
    lock = EmailDbLock("attachment_text_backfill")
    if not lock.acquire():
        return {"skipped": True, "reason": f"locked by {read_lock_owner()}"}
    try:
        con = mod.connect_db()
        try:
            result = mod.backfill_attachment_text(con, limit=batch_size)
            con.commit()
        finally:
            con.close()
    finally:
        lock.release()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=100, help="Records per batch")
    parser.add_argument("--limit", type=int, default=0, help="Total limit (0=all)")
    args = parser.parse_args()

    wait_for_priority_backfill()

    mod = load_email_search_index()
    mod.WORKSPACE_ROOT = WORKSPACE
    mod.EMAIL_ROOT = WORKSPACE / "paperless_consume" / "email"
    mod.DB_PATH = HOST_DB_PATH
    mod.STATE_PATH = WORKSPACE / "email_search_state.json"
    mod.STATUS_PATH = WORKSPACE / "email_search_harness_status.json"
    mod.FILTER_PATH = WORKSPACE / "email_rag_sender_filters.json"
    mod.TOKEN_PATH = WORKSPACE / "token.json"
    mod.LEGACY_TOKEN_PATH = WORKSPACE.parent / "work" / "token.json"
    mod.CREDS_PATH = WORKSPACE / "credentials.json"
    mod.LEGACY_CREDS_PATH = WORKSPACE / "credentials.json"

    total_remaining = count_remaining(mod)
    status = {
        "startedAt": now_jst(),
        "stage": "running",
        "totalRemaining": total_remaining,
        "batch": args.batch,
        "limit": args.limit,
        "totalUpdated": 0,
        "totalErrors": 0,
        "batches": [],
    }
    write_status(status)
    print(f"[{now_jst()}] {total_remaining} Gmail records need attachment text extraction.", flush=True)

    processed = 0
    batch_num = 0
    while True:
        remaining = count_remaining(mod)
        if remaining == 0:
            break
        if args.limit > 0 and processed >= args.limit:
            break

        effective_batch = args.batch
        if args.limit > 0:
            effective_batch = min(effective_batch, args.limit - processed)

        batch_num += 1
        result = run_batch(mod, effective_batch)
        if result.get("skipped"):
            print(f"[{now_jst()}] Batch {batch_num}: skipped ({result.get('reason')})", flush=True)
            time.sleep(10)
            continue

        updated = result.get("updated", 0)
        errors = result.get("errors", 0)
        candidates = result.get("candidates", 0)
        processed += candidates
        status["totalUpdated"] += updated
        status["totalErrors"] += errors
        status["batches"].append({
            "batch": batch_num,
            "candidates": candidates,
            "updated": updated,
            "errors": errors,
            "remaining": remaining - candidates,
            "at": now_jst(),
        })
        write_status(status)
        print(
            f"[{now_jst()}] Batch {batch_num}: candidates={candidates} updated={updated} errors={errors} remaining={remaining - candidates}",
            flush=True,
        )

        if candidates == 0:
            break
        time.sleep(2)

    status["stage"] = "completed"
    status["finishedAt"] = now_jst()
    status["ok"] = status["totalErrors"] == 0
    write_status(status)
    print(f"[{now_jst()}] Done. totalUpdated={status['totalUpdated']} totalErrors={status['totalErrors']}", flush=True)


if __name__ == "__main__":
    main()
