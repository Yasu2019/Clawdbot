#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from docker_runtime import docker_command, is_docker_runtime_command
from email_db_lock import EmailDbLock, read_lock_owner


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).absolute()
WORKSPACE = SCRIPT_PATH.parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "email_continuous_ingest_status.json"
STATE_PATH = WORKSPACE / "email_continuous_ingest_state.json"
HARNESS_STATUS_PATH = ROOT / "data" / "state" / "email_continuous_ingest" / "harness_status.json"
BACKFILL_STATUS_PATH = WORKSPACE / "gmail_priority_backfill_status.json"
DB_REPAIR_STATUS_PATH = WORKSPACE / "email_search_db_repair_status.json"
CONTAINER_NAME = "clawstack-unified-clawdbot-gateway-1"
HOST_DB_PATH = WORKSPACE / "email_search.db"
HOST_STATE_PATH = WORKSPACE / "email_search_state.json"
CONTAINER_TEMP_DB = "/tmp/email_search_incremental.db"
CONTAINER_TEMP_STATE = "/tmp/email_search_incremental_state.json"
DB_CORRUPTION_SIGNATURES = (
    "database disk image is malformed",
    "temp integrity_check failed",
    "integrity_check failed",
    "freelist: size is",
    "malformed",
)


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
    attempts = 3 if is_docker_runtime_command(command) else 1
    last_result: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
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
            result = {
                "command": " ".join(command),
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "timedOut": False,
                "attempt": attempt,
            }
        except subprocess.TimeoutExpired as exc:
            result = {
                "command": " ".join(command),
                "returncode": None,
                "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
                "timedOut": True,
                "timeoutSeconds": timeout_seconds,
                "attempt": attempt,
            }
        last_result = result
        stderr_text = str(result.get("stderr") or "")
        transient_docker_error = (
            is_docker_runtime_command(command)
            and ("500 Internal Server Error" in stderr_text or "dockerDesktopLinuxEngine" in stderr_text)
        )
        if transient_docker_error and attempt < attempts:
            time.sleep(3 * attempt)
            continue
        return result
    return last_result or {
        "command": " ".join(command),
        "returncode": 1,
        "stdout": "",
        "stderr": "unknown command failure",
        "timedOut": False,
        "attempt": 1,
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


def is_db_corruption_error(*texts: str | None) -> bool:
    haystack = "\n".join(str(text or "") for text in texts).lower()
    return any(signature in haystack for signature in DB_CORRUPTION_SIGNATURES)


def run_db_repair(timeout_seconds: int = 3600) -> dict[str, Any]:
    return run_command(
        [
            "python",
            str(WORKSPACE / "repair_email_search_db.py"),
            "--skip-stop-processes",
        ],
        timeout_seconds=timeout_seconds,
    )


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


def stage_incremental_temp_files(temp_db_host: Path, temp_state_host: Path) -> None:
    clone_db_via_backup(HOST_DB_PATH, temp_db_host)
    if HOST_STATE_PATH.exists():
        shutil.copy2(HOST_STATE_PATH, temp_state_host)
    else:
        temp_state_host.write_text("{}", encoding="utf-8")
    run_command(docker_command("cp", str(temp_db_host), f"{CONTAINER_NAME}:{CONTAINER_TEMP_DB}"), 120)
    run_command(docker_command("cp", str(temp_state_host), f"{CONTAINER_NAME}:{CONTAINER_TEMP_STATE}"), 120)


def collect_incremental_temp_files(temp_db_host: Path, temp_state_host: Path) -> None:
    run_command(docker_command("cp", f"{CONTAINER_NAME}:{CONTAINER_TEMP_DB}", str(temp_db_host)), 120)
    run_command(docker_command("cp", f"{CONTAINER_NAME}:{CONTAINER_TEMP_STATE}", str(temp_state_host)), 120)


def incremental_container_script(gmail_max_messages: int, gmail_fallback_days: int, force_query: str | None) -> str:
    force_query_literal = json.dumps(force_query, ensure_ascii=False)
    return f"""
import importlib.util, json, sys, traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location("email_search_index", "/home/node/clawd/email_search_index.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

temp_db = Path("{CONTAINER_TEMP_DB}")
temp_state = Path("{CONTAINER_TEMP_STATE}")

mod.DB_PATH = temp_db
mod.STATE_PATH = temp_state
state = mod.load_json(mod.STATE_PATH)
maintenance = state.setdefault("maintenance", {{}})
con = None

def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

try:
    con = mod.connect_db()
    eml_state = state.setdefault("eml", {{}})
    last_eml_scan_at = parse_iso(maintenance.get("lastEmlScanAt") or eml_state.get("last_scan_at"))
    now_dt = datetime.now(timezone.utc).astimezone()
    eml_scan_due = last_eml_scan_at is None or (now_dt - last_eml_scan_at.astimezone(now_dt.tzinfo)) >= timedelta(hours={12})
    if eml_scan_due:
        eml_result = mod.index_eml(con, state, None)
        con.commit()
        maintenance["lastEmlScanAt"] = mod.now_iso()
        eml_result["scanMode"] = "full"
    else:
        eml_result = {{
            "total": int(eml_state.get("known_files", 0) or 0),
            "indexed": 0,
            "skipped": int(eml_state.get("known_files", 0) or 0),
            "deleted": 0,
            "errors": 0,
            "scanMode": "skipped_recent",
        }}
    gmail_result = mod.index_gmail(con, state, {gmail_max_messages}, {gmail_fallback_days}, {force_query_literal})
    con.commit()
    changes = int(eml_result.get("indexed", 0)) + int(eml_result.get("deleted", 0)) + int(gmail_result.get("indexed", 0))
    last_rebuild_at = parse_iso(maintenance.get("lastTasksRebuildAt"))
    rebuild_due = changes > 0 and (
        last_rebuild_at is None or (now_dt - last_rebuild_at.astimezone(now_dt.tzinfo)) >= timedelta(hours={24})
    )
    rebuilt = 0
    rebuild_reason = "skipped"
    if rebuild_due:
        rebuilt = mod.rebuild_tasks(con)
        con.commit()
        maintenance["lastTasksRebuildAt"] = mod.now_iso()
        rebuild_reason = "interval_due"
    elif changes <= 0:
        rebuild_reason = "no_changes"
    else:
        rebuild_reason = "recent_rebuild"
    state["updatedAt"] = mod.now_iso()
    mod.save_json(mod.STATE_PATH, state)
    summary = {{
        "task": "email_search_index",
        "stage": "completed",
        "updatedAt": mod.now_iso(),
        "dbPath": str(temp_db),
        "eml": eml_result,
        "gmail": gmail_result,
        "taskCount": con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        "rebuiltTasks": rebuilt,
        "taskRebuildReason": rebuild_reason,
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


def run_incremental_index(
    gmail_max_messages: int,
    gmail_fallback_days: int,
    force_query: str | None,
    status: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    command = [
        "python",
        str(WORKSPACE / "host_gmail_incremental_sync.py"),
        "--gmail-max-messages",
        str(gmail_max_messages),
        "--gmail-fallback-days",
        str(gmail_fallback_days),
    ]
    if force_query:
        command.extend(["--gmail-force-query", force_query])

    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.Popen(
        command,
        **popen_kwargs,
    )

    started = time.monotonic()
    heartbeat_every_seconds = 30
    timed_out = False
    while proc.poll() is None:
        if (time.monotonic() - started) >= timeout_seconds:
            timed_out = True
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            break
        time.sleep(heartbeat_every_seconds)
        status["updatedAt"] = now_jst_text()
        status["stage"] = "indexing"
        status["currentTask"] = "incremental_index"
        status["indexHeartbeatAt"] = now_jst_text()
        write_status(status)

    stdout, stderr = proc.communicate()
    return {
        "command": " ".join(command),
        "returncode": None if timed_out else proc.returncode,
        "stdout": (stdout or "").strip(),
        "stderr": (stderr or "").strip(),
        "timedOut": timed_out,
    }

def run_command_with_heartbeat(command: list[str], timeout_seconds: int, status: dict[str, Any], stage: str, task_name: str) -> dict[str, Any]:
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.Popen(
        command,
        **popen_kwargs,
    )

    started = time.monotonic()
    heartbeat_every_seconds = 30
    timed_out = False
    
    while proc.poll() is None:
        if (time.monotonic() - started) >= timeout_seconds:
            timed_out = True
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            break
            
        time.sleep(heartbeat_every_seconds)
        status["updatedAt"] = now_jst_text()
        status["stage"] = stage
        status["currentTask"] = task_name
        status[f"{task_name}HeartbeatAt"] = now_jst_text()
        write_status(status)

    stdout, stderr = proc.communicate()
    return {
        "command": " ".join(command),
        "returncode": None if timed_out else proc.returncode,
        "stdout": (stdout or "").strip(),
        "stderr": (stderr or "").strip(),
        "timedOut": timed_out,
    }


def run_full_backfill(status: dict[str, Any]) -> dict[str, Any]:
    return run_command_with_heartbeat(
        ["python3", str(WORKSPACE / "run_priority_gmail_backfill.py")],
        timeout_seconds=5400,
        status=status,
        stage="full_backfill",
        task_name="priority_backfill",
    )


def run_learning_sync(status: dict[str, Any]) -> dict[str, Any]:
    return run_command_with_heartbeat(
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
        status=status,
        stage="sync_learning",
        task_name="learning_sync",
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
        "indexTimeoutSeconds": args.gmail_index_timeout_seconds,
        "lastSuccessAt": state.get("lastSuccessAt"),
        "lastFullBackfillAt": last_full_backfill_at,
        "lastRepairAt": state.get("lastRepairAt"),
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
    parser.add_argument("--gmail-force-query")
    parser.add_argument("--gmail-index-timeout-seconds", type=int, default=900)
    parser.add_argument("--db-repair-cooldown-minutes", type=int, default=180)
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
        status["currentTask"] = "incremental_index"
        write_status(status)

        index_result = run_incremental_index(
            args.gmail_max_messages,
            args.gmail_fallback_days,
            args.gmail_force_query,
            status,
            args.gmail_index_timeout_seconds,
        )
        index_summary = parse_latest_json(index_result.get("stdout", ""))
        status["lastIndexResult"] = index_result
        status["lastSummary"]["index"] = index_summary

        had_error = bool(index_result.get("timedOut") or index_result.get("returncode") not in (0, None))
        if had_error:
            if index_result.get("skippedLocked"):
                status["stage"] = "idle"
                status["lastError"] = ""
                status["updatedAt"] = now_jst_text()
                status["currentTask"] = "waiting_for_lock"
                write_status(status)
                time.sleep(max(args.poll_seconds, 60))
                continue
            error_text = index_result.get("stderr") or index_result.get("stdout") or "incremental index failed"
            if is_db_corruption_error(error_text, index_summary.get("error"), index_summary.get("traceback")):
                last_repair_dt = parse_dt(status.get("lastRepairAt"))
                repair_allowed = (
                    last_repair_dt is None
                    or (now_jst().astimezone(last_repair_dt.tzinfo) - last_repair_dt)
                    >= timedelta(minutes=args.db_repair_cooldown_minutes)
                )
                if repair_allowed:
                    status["stage"] = "db_repair"
                    status["currentTask"] = "repair_email_search_db"
                    status["lastError"] = error_text
                    status["updatedAt"] = now_jst_text()
                    write_status(status)
                    repair_result = run_db_repair()
                    repair_summary = load_json(DB_REPAIR_STATUS_PATH, {})
                    status["lastRepairResult"] = repair_result
                    status["lastSummary"]["repair"] = repair_summary
                    status["lastRepairAt"] = now_jst_text()
                    if repair_result.get("returncode") == 0 and repair_summary.get("stage") == "completed":
                        status["stage"] = "idle"
                        status["currentTask"] = "repair_completed_waiting"
                        status["lastError"] = ""
                        status["updatedAt"] = now_jst_text()
                        write_status(status)
                        save_json(
                            STATE_PATH,
                            {
                                "cycle": cycle,
                                "lastSuccessAt": status.get("lastSuccessAt"),
                                "lastFullBackfillAt": last_full_backfill_at,
                                "lastRepairAt": status.get("lastRepairAt"),
                                "lastSummary": status.get("lastSummary", {}),
                            },
                        )
                        time.sleep(5)
                        continue
                    status["stage"] = "error"
                    status["currentTask"] = "repair_failed"
                    status["lastError"] = repair_result.get("stderr") or repair_summary.get("error") or error_text
                    status["updatedAt"] = now_jst_text()
                    write_status(status)
                    if args.once:
                        break
                    time.sleep(max(args.poll_seconds, 60))
                    continue
            status["stage"] = "error"
            status["lastError"] = error_text
            status["updatedAt"] = now_jst_text()
            write_status(status)
            if args.once:
                break
            time.sleep(max(args.poll_seconds, 60))
            continue

        if cycle == 1 or cycle % args.learning_interval_cycles == 0:
            status["stage"] = "sync_learning"
            status["updatedAt"] = now_jst_text()
            status["currentTask"] = "learning_sync"
            write_status(status)
            learning_result = run_learning_sync(status)
            status["lastLearningSyncResult"] = learning_result
            status["lastSummary"]["learning"] = parse_latest_json(learning_result.get("stdout", ""))
            if learning_result.get("timedOut") or learning_result.get("returncode") not in (0, None):
                status["lastError"] = learning_result.get("stderr") or "learning sync failed"
            else:
                status["lastError"] = ""
            if args.once and status.get("lastError"):
                status["stage"] = "error"
                status["updatedAt"] = now_jst_text()
                write_status(status)
                break

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
            status["currentTask"] = "priority_backfill"
            write_status(status)
            backfill_result = run_full_backfill(status)
            status["lastBackfillResult"] = backfill_result
            status["lastSummary"]["backfill"] = parse_latest_json(backfill_result.get("stdout", ""))
            backfill_ok = bool(
                backfill_result.get("returncode") == 0
                and not backfill_result.get("timedOut")
                and status["lastSummary"]["backfill"].get("ok", True)
            )
            if backfill_ok:
                last_full_backfill_at = now_jst_text()
                status["lastFullBackfillAt"] = last_full_backfill_at
            else:
                status["lastError"] = backfill_result.get("stderr") or "full backfill failed"
            if args.once and status.get("lastError"):
                status["stage"] = "error"
                status["updatedAt"] = now_jst_text()
                write_status(status)
                break

        status["stage"] = "dashboard_refresh"
        status["updatedAt"] = now_jst_text()
        status["currentTask"] = "dashboard_refresh"
        write_status(status)
        dashboard_result = run_dashboard_refresh()
        status["lastDashboardResult"] = dashboard_result

        status["stage"] = "idle"
        status["updatedAt"] = now_jst_text()
        status["currentTask"] = "sleeping"
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
                "lastRepairAt": status.get("lastRepairAt"),
                "lastSummary": status.get("lastSummary", {}),
            },
        )
        if args.once:
            break
        time.sleep(max(args.poll_seconds, 60))


if __name__ == "__main__":
    main()
