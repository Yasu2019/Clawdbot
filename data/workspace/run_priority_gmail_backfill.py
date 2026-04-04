#!/usr/bin/env python3
import json
import subprocess
import sqlite3
import shutil
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from docker_runtime import docker_command, is_docker_runtime_command
from email_db_lock import EmailDbLock, read_lock_owner


JST = timezone(timedelta(hours=9))
START_DATE = date(2026, 1, 1)
MAX_MESSAGES_PER_CHUNK = 5000
TIMEOUT_SECONDS = 3600
CONTAINER_NAME = "clawstack-unified-clawdbot-gateway-1"

SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
STATUS_PATH = SCRIPT_PATH.parent / "gmail_priority_backfill_status.json"
HOST_DB_PATH = WORKSPACE / "email_search.db"
HOST_STATE_PATH = WORKSPACE / "email_search_state.json"
CONTAINER_TEMP_DB = "/tmp/email_search_priority_backfill.db"
CONTAINER_TEMP_STATE = "/tmp/email_search_priority_backfill_state.json"


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


def run_command(command: list[str], timeout_seconds: int) -> dict:
    attempts = 3 if is_docker_runtime_command(command) else 1
    last_result: dict | None = None
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        result = {
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
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
        "returncode": 1,
        "stdout": "",
        "stderr": "unknown command failure",
        "timedOut": False,
        "attempt": 1,
    }


def stage_temp_files(temp_db_host: Path, temp_state_host: Path) -> None:
    clone_db_via_backup(HOST_DB_PATH, temp_db_host)
    if HOST_STATE_PATH.exists():
        shutil.copy2(HOST_STATE_PATH, temp_state_host)
    else:
        temp_state_host.write_text("{}", encoding="utf-8")
    run_command(docker_command("cp", str(temp_db_host), f"{CONTAINER_NAME}:{CONTAINER_TEMP_DB}"), 300)
    run_command(docker_command("cp", str(temp_state_host), f"{CONTAINER_NAME}:{CONTAINER_TEMP_STATE}"), 120)


def collect_temp_files(temp_db_host: Path, temp_state_host: Path) -> None:
    run_command(docker_command("cp", f"{CONTAINER_NAME}:{CONTAINER_TEMP_DB}", str(temp_db_host)), 300)
    run_command(docker_command("cp", f"{CONTAINER_NAME}:{CONTAINER_TEMP_STATE}", str(temp_state_host)), 120)


def container_script(chunks: list[dict]) -> str:
    payload = json.dumps(chunks, ensure_ascii=False)
    return f"""
import importlib.util, json, sys, traceback
import sqlite3
from pathlib import Path

spec = importlib.util.spec_from_file_location("email_search_index", "/home/node/clawd/email_search_index.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

chunks = json.loads({payload!r})
temp_db = Path("{CONTAINER_TEMP_DB}")
temp_state = Path("{CONTAINER_TEMP_STATE}")

mod.DB_PATH = temp_db
mod.STATE_PATH = temp_state
state = mod.load_json(mod.STATE_PATH)
results = []
con = None

try:
    con = mod.connect_db()
    for chunk in chunks:
        gmail_result = mod.index_gmail(con, state, {MAX_MESSAGES_PER_CHUNK}, 30, chunk["query"])
        con.commit()
        rebuilt = mod.rebuild_tasks(con)
        con.commit()
        results.append({{
            "startDate": chunk["startDate"],
            "endDateInclusive": chunk["endDateInclusive"],
            "query": chunk["query"],
            "gmail": gmail_result,
            "rebuiltTasks": rebuilt,
        }})
    state["updatedAt"] = mod.now_iso()
    mod.save_json(mod.STATE_PATH, state)
    integrity = sqlite3.connect(temp_db).execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"temp db integrity_check failed: {{integrity}}")
    summary = {{"ok": True, "chunks": results}}
    print(json.dumps(summary, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({{
        "ok": False,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "chunks": results,
    }}, ensure_ascii=False))
    raise
finally:
    if con is not None:
        con.close()
"""


def run_backfill(chunks: list[dict]) -> dict:
    tempdir = Path(tempfile.mkdtemp(prefix="email_backfill_"))
    temp_db_host = tempdir / "email_search_priority_backfill.db"
    temp_state_host = tempdir / "email_search_priority_backfill_state.json"
    stage_temp_files(temp_db_host, temp_state_host)
    proc = subprocess.run(
        docker_command("exec", "-i", CONTAINER_NAME, "python3", "-"),
        input=container_script(chunks),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
    )
    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "timedOut": False,
    }
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            result["summary"] = json.loads(line)
            break
        except Exception:
            continue
    if result.get("returncode") == 0 and result.get("summary", {}).get("ok"):
        collect_temp_files(temp_db_host, temp_state_host)
        con = sqlite3.connect(temp_db_host)
        try:
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            con.close()
        if integrity != "ok":
            result["returncode"] = 1
            result["stderr"] = f"host temp integrity_check failed: {integrity}"
        else:
            promote_db_via_backup(temp_db_host, HOST_DB_PATH)
            if temp_state_host.exists():
                shutil.copy2(temp_state_host, HOST_STATE_PATH)
    return result


def main() -> None:
    yesterday = datetime.now(JST).date() - timedelta(days=1)
    chunks = month_chunks(START_DATE, yesterday)
    lock = EmailDbLock("priority_backfill")
    status = {
        "startedAt": now_jst(),
        "stage": "running",
        "startDate": START_DATE.isoformat(),
        "endDateInclusive": yesterday.isoformat(),
        "maxMessagesPerChunk": MAX_MESSAGES_PER_CHUNK,
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
        result = run_backfill(chunks)
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
