#!/usr/bin/env python3
import argparse
import importlib.util
import json
import subprocess
import sqlite3
import shutil
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from email_db_lock import EmailDbLock, read_lock_owner


JST = timezone(timedelta(hours=9))
START_DATE = date(2019, 1, 1)
MAX_MESSAGES_PER_CHUNK = 500
TIMEOUT_SECONDS = 3600

SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
STATUS_PATH = SCRIPT_PATH.parent / "gmail_priority_backfill_status.json"
HOST_DB_PATH = WORKSPACE / "email_search.db"
HOST_STATE_PATH = WORKSPACE / "email_search_state.json"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def month_chunks(start_date: date, end_date_inclusive: date) -> list[dict]:
    chunks: list[dict] = []
    cursor = start_date
    while cursor <= end_date_inclusive:
        if cursor.month == 12:
            next_month = date(cursor.year + 1, 1, 1)
        else:
            next_month = date(cursor.year, cursor.month + 1, 1)
        chunk_end = min(end_date_inclusive, next_month - timedelta(days=1))
        start_anchor = cursor - timedelta(days=1)
        chunks.append(
            {
                "startDate": cursor.isoformat(),
                "endDateInclusive": chunk_end.isoformat(),
                "query": f"in:anywhere after:{start_anchor.strftime('%Y/%m/%d')} before:{(chunk_end + timedelta(days=1)).strftime('%Y/%m/%d')}",
            }
        )
        cursor = chunk_end + timedelta(days=1)
    return chunks


def clone_db_via_backup(src_path: Path, dst_path: Path) -> None:
    src_con = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=30)
    dst_con = sqlite3.connect(dst_path, timeout=30)
    try:
        src_con.backup(dst_con)
        dst_con.commit()
    finally:
        dst_con.close()
        src_con.close()


def promote_db_via_backup(src_path: Path, dst_path: Path) -> None:
    src_con = sqlite3.connect(src_path, timeout=30)
    dst_con = sqlite3.connect(dst_path, timeout=30)
    try:
        try:
            dst_con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        src_con.backup(dst_con)
        dst_con.commit()
    finally:
        dst_con.close()
        src_con.close()


def stage_temp_files(temp_db_host: Path, temp_state_host: Path) -> None:
    clone_db_via_backup(HOST_DB_PATH, temp_db_host)
    if HOST_STATE_PATH.exists():
        shutil.copy2(HOST_STATE_PATH, temp_state_host)
    else:
        temp_state_host.write_text("{}", encoding="utf-8")

def load_email_search_index():
    spec = importlib.util.spec_from_file_location("email_search_index", str(WORKSPACE / "email_search_index.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_backfill(chunks: list[dict], max_messages_per_chunk: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="email_backfill_") as tempdir_raw:
        tempdir = Path(tempdir_raw)
        temp_db_host = tempdir / "email_search_priority_backfill.db"
        temp_state_host = tempdir / "email_search_priority_backfill_state.json"
        stage_temp_files(temp_db_host, temp_state_host)
        result = {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timedOut": False,
        }
        mod = load_email_search_index()
        mod.WORKSPACE_ROOT = WORKSPACE
        mod.EMAIL_ROOT = WORKSPACE / "paperless_consume" / "email"
        mod.DB_PATH = temp_db_host
        mod.STATE_PATH = temp_state_host
        mod.STATUS_PATH = WORKSPACE / "email_search_harness_status.json"
        mod.FILTER_PATH = WORKSPACE / "email_rag_sender_filters.json"
        mod.TOKEN_PATH = WORKSPACE / "token.json"
        mod.LEGACY_TOKEN_PATH = WORKSPACE.parent / "work" / "token.json"
        mod.CREDS_PATH = WORKSPACE / "credentials.json"
        mod.LEGACY_CREDS_PATH = WORKSPACE / "credentials.json"

        state = mod.load_json(mod.STATE_PATH)
        con = None
        chunk_results: list[dict] = []
        try:
            con = mod.connect_db()
            for chunk in chunks:
                gmail_result = mod.index_gmail(con, state, max_messages_per_chunk, 30, chunk["query"])
                con.commit()
                rebuilt = mod.rebuild_tasks(con)
                con.commit()
                chunk_results.append(
                    {
                        "startDate": chunk["startDate"],
                        "endDateInclusive": chunk["endDateInclusive"],
                        "query": chunk["query"],
                        "gmail": gmail_result,
                        "rebuiltTasks": rebuilt,
                    }
                )
            state["updatedAt"] = mod.now_iso()
            mod.save_json(mod.STATE_PATH, state)
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        except Exception as exc:
            result["returncode"] = 1
            result["stderr"] = str(exc)
            result["summary"] = {
                "ok": False,
                "error": str(exc),
                "chunks": chunk_results,
            }
        finally:
            if con is not None:
                con.close()

        if result.get("returncode") == 0:
            if integrity != "ok":
                result["returncode"] = 1
                result["stderr"] = f"host temp integrity_check failed: {integrity}"
                result["summary"] = {
                    "ok": False,
                    "error": result["stderr"],
                    "chunks": chunk_results,
                }
            else:
                promote_db_via_backup(temp_db_host, HOST_DB_PATH)
                if temp_state_host.exists():
                    shutil.copy2(temp_state_host, HOST_STATE_PATH)
                result["summary"] = {
                    "ok": True,
                    "chunks": chunk_results,
                }
        result["stdout"] = json.dumps(result.get("summary", {}), ensure_ascii=False)
        return result


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Priority Gmail backfill starting from 2026-01-01")
    parser.add_argument("--start-date", type=parse_date_arg, default=START_DATE)
    parser.add_argument("--end-date", type=parse_date_arg)
    parser.add_argument("--max-messages-per-chunk", type=int, default=MAX_MESSAGES_PER_CHUNK)
    args = parser.parse_args()

    yesterday = datetime.now(JST).date() - timedelta(days=1)
    end_date = args.end_date or yesterday
    if end_date > yesterday:
        end_date = yesterday
    if args.start_date > end_date:
        raise SystemExit("start-date must be on or before end-date")

    chunks = month_chunks(args.start_date, end_date)
    lock = EmailDbLock("priority_backfill")
    status = {
        "startedAt": now_jst(),
        "stage": "running",
        "startDate": args.start_date.isoformat(),
        "endDateInclusive": end_date.isoformat(),
        "maxMessagesPerChunk": args.max_messages_per_chunk,
        "chunks": chunks,
    }
    write_status(status)
    if not lock.acquire():
        status["stage"] = "completed"
        status["finishedAt"] = now_jst()
        status["ok"] = False
        status["result"] = {
            "returncode": 2,
            "stdout": "",
            "stderr": f"email db operations locked by {read_lock_owner()}",
            "timedOut": False,
        }
        write_status(status)
        print(json.dumps(status, ensure_ascii=False))
        raise SystemExit(2)
    try:
        result = run_backfill(chunks, args.max_messages_per_chunk)
        status["result"] = result
        status["ok"] = bool(result.get("returncode") == 0 and result.get("summary", {}).get("ok"))
    except subprocess.TimeoutExpired as exc:
        status["result"] = {
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": TIMEOUT_SECONDS,
        }
        status["ok"] = False
    status["stage"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)
    lock.release()
    print(json.dumps(status, ensure_ascii=False))
    if not status.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
