#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "email_continuous_ingest_status.json"
STATE_PATH = WORKSPACE / "email_continuous_ingest_state.json"
HARNESS_STATUS_PATH = ROOT / "data" / "state" / "email_continuous_ingest" / "harness_status.json"
BACKFILL_STATUS_PATH = WORKSPACE / "gmail_priority_backfill_status.json"
CONTAINER_NAME = "clawstack-unified-clawdbot-gateway-1"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def write_status(status: dict[str, Any]) -> None:
    save_json(STATUS_PATH, status)
    harness = {
        "service": "email_continuous_ingest",
        "updatedAt": now_jst().isoformat(),
        "pid": os.getpid(),
        "state": status.get("stage", "unknown"),
        "cycle": status.get("cycle", 0),
        "lastSuccessAt": status.get("lastSuccessAt"),
        "lastError": status.get("lastError"),
        "lastSummary": status.get("lastSummary", {}),
    }
    save_json(HARNESS_STATUS_PATH, harness)


def run_command(command: list[str], timeout_seconds: int, stdin_text: str | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": timeout_seconds,
        }


def parse_latest_json(stdout: str) -> dict[str, Any]:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except Exception:
            continue
    return {}


def incremental_container_script(gmail_max_messages: int, gmail_fallback_days: int) -> str:
    return f"""
import importlib.util, json, shutil, sys, traceback
import sqlite3
from pathlib import Path

spec = importlib.util.spec_from_file_location("email_search_index", "/home/node/clawd/email_search_index.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

host_db = Path("/home/node/clawd/email_search.db")
host_state = Path("/home/node/clawd/email_search_state.json")
temp_db = Path("/tmp/email_search_incremental.db")
temp_state = Path("/tmp/email_search_incremental_state.json")

def clone_db(src_path: Path, dst_path: Path) -> None:
    src_con = sqlite3.connect(f"file:{{src_path}}?mode=ro", uri=True, timeout=30)
    dst_con = sqlite3.connect(dst_path, timeout=30)
    try:
        src_con.backup(dst_con)
        dst_con.commit()
    finally:
        dst_con.close()
        src_con.close()

clone_db(host_db, temp_db)
if host_state.exists():
    shutil.copy2(host_state, temp_state)

mod.DB_PATH = temp_db
mod.STATE_PATH = temp_state
state = mod.load_json(mod.STATE_PATH)
    con = None

def promote_temp_db(src_path: Path, dst_path: Path) -> None:
    src_con = sqlite3.connect(src_path)
    dst_con = sqlite3.connect(dst_path, timeout=30)
    try:
        src_con.execute("PRAGMA quick_check")
        try:
            dst_con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        src_con.backup(dst_con)
        dst_con.commit()
    finally:
        dst_con.close()
        src_con.close()

try:
    con = mod.connect_db()
    eml_result = mod.index_eml(con, state, None)
    con.commit()
    gmail_result = mod.index_gmail(con, state, {gmail_max_messages}, {gmail_fallback_days}, None)
    con.commit()
    rebuilt = mod.rebuild_tasks(con)
    con.commit()
    state["updatedAt"] = mod.now_iso()
    mod.save_json(mod.STATE_PATH, state)
    integrity = sqlite3.connect(temp_db).execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"temp db integrity_check failed: {{integrity}}")
    promote_temp_db(temp_db, host_db)
    if temp_state.exists():
        shutil.copy2(temp_state, host_state)
    summary = {{
        "task": "email_search_index",
        "stage": "completed",
        "updatedAt": mod.now_iso(),
        "dbPath": str(host_db),
        "eml": eml_result,
        "gmail": gmail_result,
        "taskCount": con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        "rebuiltTasks": rebuilt,
    }}
    print(json.dumps(summary, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({{
        "task": "email_search_index",
        "stage": "error",
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }}, ensure_ascii=False))
    raise
finally:
    if con is not None:
        con.close()
"""


def run_incremental_index(gmail_max_messages: int, gmail_fallback_days: int) -> dict[str, Any]:
    return run_command(
        ["docker", "exec", "-i", CONTAINER_NAME, "python3", "-"],
        timeout_seconds=1200,
        stdin_text=incremental_container_script(gmail_max_messages, gmail_fallback_days),
    )


def run_full_backfill() -> dict[str, Any]:
    return run_command(
        ["python3", str(WORKSPACE / "run_priority_gmail_backfill.py")],
        timeout_seconds=5400,
    )


def run_learning_sync() -> dict[str, Any]:
    return run_command(
        [
            "python3",
            str(WORKSPACE / "sync_email_learning_memory.py"),
            "--base-url",
            "http://localhost:8110",
            "--source-org",
            "Mitsui",
            "--bootstrap-days",
            "30",
            "--limit",
            "800",
        ],
        timeout_seconds=1800,
    )


def run_dashboard_refresh() -> dict[str, Any]:
    return run_command(
        ["python3", str(WORKSPACE / "update_email_ingest_dashboard_status.py")],
        timeout_seconds=120,
    )


def build_initial_status(args: argparse.Namespace) -> dict[str, Any]:
    state = load_json(STATE_PATH, {})
    backfill = load_json(BACKFILL_STATUS_PATH, {})
    last_full_backfill_at = (
        state.get("lastFullBackfillAt")
        or backfill.get("finishedAt")
        or backfill.get("startedAt")
    )
    return {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "stage": "starting",
        "pid": os.getpid(),
        "cycle": int(state.get("cycle", 0)),
        "pollSeconds": args.poll_seconds,
        "learningIntervalCycles": args.learning_interval_cycles,
        "fullBackfillIntervalCycles": args.full_backfill_interval_cycles,
        "lastSuccessAt": state.get("lastSuccessAt"),
        "lastFullBackfillAt": last_full_backfill_at,
        "lastSummary": state.get("lastSummary", {}),
        "lastError": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuously ingest Gmail into SQLite and Learning Memory")
    parser.add_argument("--poll-seconds", type=int, default=300)
    parser.add_argument("--learning-interval-cycles", type=int, default=3)
    parser.add_argument("--full-backfill-interval-cycles", type=int, default=72)
    parser.add_argument("--gmail-max-messages", type=int, default=200)
    parser.add_argument("--gmail-fallback-days", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip-full-backfill", action="store_true")
    args = parser.parse_args()

    status = build_initial_status(args)
    write_status(status)

    state = load_json(STATE_PATH, {})
    cycle = int(state.get("cycle", 0))
    last_full_backfill_at = status.get("lastFullBackfillAt")

    while True:
        cycle += 1
        status["cycle"] = cycle
        status["updatedAt"] = now_jst_text()
        status["stage"] = "indexing"
        write_status(status)

        index_result = run_incremental_index(args.gmail_max_messages, args.gmail_fallback_days)
        index_summary = parse_latest_json(index_result.get("stdout", ""))
        status["lastIndexResult"] = index_result
        status["lastSummary"]["index"] = index_summary

        had_error = bool(index_result.get("timedOut") or index_result.get("returncode") not in (0, None))
        if had_error:
            status["stage"] = "error"
            status["lastError"] = index_result.get("stderr") or "incremental index failed"
            status["updatedAt"] = now_jst_text()
            write_status(status)
            time.sleep(max(args.poll_seconds, 60))
            continue

        if cycle == 1 or cycle % args.learning_interval_cycles == 0:
            status["stage"] = "sync_learning"
            status["updatedAt"] = now_jst_text()
            write_status(status)
            learning_result = run_learning_sync()
            status["lastLearningSyncResult"] = learning_result
            status["lastSummary"]["learning"] = parse_latest_json(learning_result.get("stdout", ""))
            if learning_result.get("timedOut") or learning_result.get("returncode") not in (0, None):
                status["lastError"] = learning_result.get("stderr") or "learning sync failed"
            else:
                status["lastError"] = ""

        last_full_backfill_dt = parse_dt(last_full_backfill_at)
        need_full_backfill = (
            not args.skip_full_backfill and (
                last_full_backfill_dt is None
                or (now_jst().astimezone(last_full_backfill_dt.tzinfo) - last_full_backfill_dt) >= timedelta(hours=12)
                or cycle % args.full_backfill_interval_cycles == 0
            )
        )
        if need_full_backfill:
            status["stage"] = "full_backfill"
            status["updatedAt"] = now_jst_text()
            write_status(status)
            backfill_result = run_full_backfill()
            status["lastBackfillResult"] = backfill_result
            status["lastSummary"]["backfill"] = parse_latest_json(backfill_result.get("stdout", ""))
            if backfill_result.get("returncode") == 0 and not backfill_result.get("timedOut"):
                last_full_backfill_at = now_jst_text()
                status["lastFullBackfillAt"] = last_full_backfill_at
            else:
                status["lastError"] = backfill_result.get("stderr") or "full backfill failed"

        status["stage"] = "dashboard_refresh"
        status["updatedAt"] = now_jst_text()
        write_status(status)
        dashboard_result = run_dashboard_refresh()
        status["lastDashboardResult"] = dashboard_result

        status["stage"] = "idle"
        status["updatedAt"] = now_jst_text()
        status["lastSuccessAt"] = now_jst_text()
        if not status.get("lastError"):
            status["lastError"] = ""
        write_status(status)

        save_json(
            STATE_PATH,
            {
                "cycle": cycle,
                "lastSuccessAt": status["lastSuccessAt"],
                "lastFullBackfillAt": last_full_backfill_at,
                "lastSummary": status.get("lastSummary", {}),
            },
        )
        if args.once:
            break
        time.sleep(max(args.poll_seconds, 60))


if __name__ == "__main__":
    main()
