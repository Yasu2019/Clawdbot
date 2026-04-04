#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).absolute().parent
ROOT = WORKSPACE.parent.parent
DB_PATH = WORKSPACE / "email_search.db"
STATE_PATH = WORKSPACE / "email_search_state.json"
BACKUP_DIR = WORKSPACE / "db_repair_backups"
STATUS_PATH = WORKSPACE / "email_search_db_repair_status.json"
WATCHDOG_START = ROOT / "scripts" / "start_email_continuous_watchdog.ps1"
INDEX_MODULE_PATH = WORKSPACE / "email_search_index.py"
TEMP_REPAIR_ROOT = Path(tempfile.gettempdir()) / "clawdbot_email_db_repair"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index_module():
    spec = importlib.util.spec_from_file_location("email_search_index_repair", INDEX_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_command(command: list[str], timeout_seconds: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
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
        }


def process_snapshot(token: str) -> list[dict[str, Any]]:
    ps = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    result = run_command(["powershell", "-NoProfile", "-Command", ps], 60)
    if not result.get("stdout"):
        return []
    try:
        payload = json.loads(result["stdout"])
    except Exception:
        return []
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def stop_processes(token: str) -> dict[str, Any]:
    before = process_snapshot(token)
    if not before:
        return {"token": token, "stopped": [], "alreadyStopped": True}
    script = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    result = run_command(["powershell", "-NoProfile", "-Command", script], 60)
    after = process_snapshot(token)
    return {
        "token": token,
        "before": before,
        "after": after,
        "commandResult": result,
        "stopped": [item.get("ProcessId") for item in before if item.get("ProcessId") not in {x.get("ProcessId") for x in after}],
    }


def backup_path_for(timestamp: str) -> Path:
    TEMP_REPAIR_ROOT.mkdir(parents=True, exist_ok=True)
    return TEMP_REPAIR_ROOT / f"email_search_pre_repair_{timestamp}.db"


def count_rows(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


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


def copy_email_range(
    src_con: sqlite3.Connection,
    dst_con: sqlite3.Connection,
    mod: Any,
    start_rowid: int,
    end_rowid: int,
    skipped: list[int],
) -> int:
    if start_rowid > end_rowid:
        return 0
    try:
        rows = src_con.execute(
            "SELECT rowid, * FROM emails WHERE rowid BETWEEN ? AND ? ORDER BY rowid",
            (start_rowid, end_rowid),
        ).fetchall()
    except sqlite3.DatabaseError:
        if start_rowid == end_rowid:
            skipped.append(start_rowid)
            return 0
        mid = (start_rowid + end_rowid) // 2
        left = copy_email_range(src_con, dst_con, mod, start_rowid, mid, skipped)
        right = copy_email_range(src_con, dst_con, mod, mid + 1, end_rowid, skipped)
        return left + right

    copied = 0
    for row in rows:
        try:
            record = mod.email_record_from_row(row)
            mod.upsert_record(dst_con, record)
            copied += 1
        except sqlite3.DatabaseError:
            skipped.append(int(row["rowid"]))
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--restart-watchdog", action="store_true")
    parser.add_argument("--source-db")
    args = parser.parse_args()

    timestamp = now_jst().strftime("%Y%m%d_%H%M%S")
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "dbPath": str(DB_PATH),
        "stage": "starting",
        "chunkSize": args.chunk_size,
    }
    write_status(status)

    stop_results = {
        "watchdog": stop_processes("email_continuous_watchdog.py"),
        "daemon": stop_processes("continuous_email_ingest_daemon.py"),
    }
    status["stopResults"] = stop_results
    status["stage"] = "backing_up"
    write_status(status)

    if args.source_db:
        backup_path = Path(args.source_db).resolve()
        status["backupPath"] = str(backup_path)
        status["movedSourceDbTo"] = str(backup_path)
        write_status(status)
    else:
        backup_path = backup_path_for(timestamp)
        status["backupPath"] = str(backup_path)
        write_status(status)
        try:
            shutil.move(str(DB_PATH), str(backup_path))
            status["backupMode"] = "move"
            status["movedSourceDbTo"] = str(backup_path)
        except PermissionError:
            clone_db_via_backup(DB_PATH, backup_path)
            status["backupMode"] = "sqlite_backup_copy"
            status["copiedSourceDbTo"] = str(backup_path)
        write_status(status)

    repaired_path = WORKSPACE / f"email_search_repaired_{timestamp}.db"
    skipped_rowids: list[int] = []
    mod = load_index_module()

    src_con = sqlite3.connect(backup_path)
    src_con.row_factory = sqlite3.Row
    dst_con = None
    try:
        min_rowid, max_rowid, email_count = src_con.execute(
            "SELECT MIN(rowid), MAX(rowid), COUNT(*) FROM emails"
        ).fetchone()
        mod.DB_PATH = repaired_path
        dst_con = mod.connect_db()
        dst_con.execute("DELETE FROM emails")
        dst_con.execute("DELETE FROM tasks")
        dst_con.commit()

        status["stage"] = "copying_emails"
        status["sourceEmailCount"] = int(email_count or 0)
        status["rowidRange"] = {"min": int(min_rowid or 0), "max": int(max_rowid or 0)}
        write_status(status)

        copied_total = 0
        start = int(min_rowid or 0)
        end = int(max_rowid or -1)
        while start <= end:
            chunk_end = min(start + args.chunk_size - 1, end)
            copied_total += copy_email_range(src_con, dst_con, mod, start, chunk_end, skipped_rowids)
            dst_con.commit()
            status["copiedEmails"] = copied_total
            status["skippedRowids"] = skipped_rowids[-20:]
            status["updatedAt"] = now_jst_text()
            write_status(status)
            start = chunk_end + 1

        status["stage"] = "rebuilding_tasks"
        write_status(status)
        rebuilt_tasks = mod.rebuild_tasks(dst_con)
        dst_con.commit()

        integrity = dst_con.execute("PRAGMA integrity_check").fetchone()[0]
        quick = dst_con.execute("PRAGMA quick_check").fetchone()[0]
        if integrity != "ok" or quick != "ok":
            raise RuntimeError(f"repaired db integrity failed: integrity={integrity} quick={quick}")

        repaired_counts = {
            "emails": count_rows(dst_con, "emails"),
            "tasks": count_rows(dst_con, "tasks"),
            "emails_fts": count_rows(dst_con, "emails_fts"),
            "tasks_fts": count_rows(dst_con, "tasks_fts"),
        }
    finally:
        if dst_con is not None:
            dst_con.close()
        src_con.close()

    status["stage"] = "swapping"
    status["repairedPath"] = str(repaired_path)
    status["copiedEmails"] = copied_total
    status["rebuiltTasks"] = rebuilt_tasks
    status["skippedRowidCount"] = len(skipped_rowids)
    status["skippedRowidsPreview"] = skipped_rowids[:20]
    status["repairedCounts"] = repaired_counts
    write_status(status)

    try:
        os.replace(repaired_path, DB_PATH)
        status["swapMode"] = "os_replace"
    except PermissionError:
        promote_db_via_backup(repaired_path, DB_PATH)
        repaired_path.unlink(missing_ok=True)
        status["swapMode"] = "sqlite_backup_promote"
    if STATE_PATH.exists():
        status["statePathPreserved"] = str(STATE_PATH)

    restart_result = None
    if args.restart_watchdog:
        restart_result = run_command(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WATCHDOG_START)],
            60,
        )

    status["stage"] = "completed"
    status["finishedAt"] = now_jst_text()
    status["restartResult"] = restart_result
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
