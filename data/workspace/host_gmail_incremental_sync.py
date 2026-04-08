#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from email_db_lock import EmailDbLock, read_lock_owner


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "host_gmail_incremental_sync_status.json"
HOST_DB_PATH = WORKSPACE / "email_search.db"
HOST_STATE_PATH = WORKSPACE / "email_search_state.json"


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def now_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


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


def load_email_search_index():
    spec = importlib.util.spec_from_file_location("email_search_index", str(WORKSPACE / "email_search_index.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_status(payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["updatedAt"] = now_text()
    save_json(STATUS_PATH, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Host-side Gmail incremental sync using temp SQLite promotion")
    parser.add_argument("--gmail-max-messages", type=int, default=20)
    parser.add_argument("--gmail-fallback-days", type=int, default=3)
    parser.add_argument("--gmail-force-query")
    parser.add_argument("--task-rebuild-interval-hours", type=int, default=24)
    args = parser.parse_args()

    lock = EmailDbLock("host_gmail_incremental_sync")
    if not lock.acquire():
        payload = {
            "task": "host_gmail_incremental_sync",
            "stage": "skipped_locked",
            "updatedAt": now_iso(),
            "error": f"email db operations locked by {read_lock_owner()}",
            "skippedLocked": True,
        }
        write_status(payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 2

    tempdir = None
    try:
        temp_root = WORKSPACE / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        tempdir = Path(tempfile.mkdtemp(prefix="host_gmail_sync_", dir=str(temp_root)))
        temp_db_path = tempdir / "email_search_incremental.db"
        temp_state_path = tempdir / "email_search_incremental_state.json"

        write_status(
            {
                "task": "host_gmail_incremental_sync",
                "stage": "starting",
                "startedAt": now_text(),
                "dbPath": str(HOST_DB_PATH),
            }
        )
        clone_db_via_backup(HOST_DB_PATH, temp_db_path)
        if HOST_STATE_PATH.exists():
            shutil.copy2(HOST_STATE_PATH, temp_state_path)
        else:
            temp_state_path.write_text("{}", encoding="utf-8")

        mod = load_email_search_index()
        mod.WORKSPACE_ROOT = WORKSPACE
        mod.EMAIL_ROOT = WORKSPACE / "paperless_consume" / "email"
        mod.DB_PATH = temp_db_path
        mod.STATE_PATH = temp_state_path
        mod.STATUS_PATH = WORKSPACE / "email_search_harness_status.json"
        mod.FILTER_PATH = WORKSPACE / "email_rag_sender_filters.json"
        mod.TOKEN_PATH = WORKSPACE / "token.json"
        mod.LEGACY_TOKEN_PATH = WORKSPACE.parent / "work" / "token.json"
        mod.CREDS_PATH = WORKSPACE / "credentials.json"
        mod.LEGACY_CREDS_PATH = WORKSPACE / "credentials.json"

        state = mod.load_json(mod.STATE_PATH)
        maintenance = state.setdefault("maintenance", {})
        con = mod.connect_db()
        try:
            write_status(
                {
                    "task": "host_gmail_incremental_sync",
                    "stage": "indexing",
                    "startedAt": now_text(),
                    "tempDbPath": str(temp_db_path),
                }
            )
            gmail_result = mod.index_gmail(
                con,
                state,
                args.gmail_max_messages,
                args.gmail_fallback_days,
                args.gmail_force_query,
            )
            con.commit()

            changes = int(gmail_result.get("indexed", 0) or 0)
            last_rebuild_at = parse_iso(maintenance.get("lastTasksRebuildAt"))
            now_dt = datetime.now(timezone.utc).astimezone()
            rebuild_due = changes > 0 and (
                last_rebuild_at is None
                or (now_dt - last_rebuild_at.astimezone(now_dt.tzinfo))
                >= timedelta(hours=args.task_rebuild_interval_hours)
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
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            task_count = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        finally:
            con.close()

        if integrity != "ok":
            raise RuntimeError(f"temp integrity_check failed: {integrity}")

        promote_db_via_backup(temp_db_path, HOST_DB_PATH)
        shutil.copy2(temp_state_path, HOST_STATE_PATH)

        payload = {
            "task": "host_gmail_incremental_sync",
            "stage": "completed",
            "updatedAt": mod.now_iso(),
            "dbPath": str(temp_db_path),
            "gmail": gmail_result,
            "taskCount": task_count,
            "rebuiltTasks": rebuilt,
            "taskRebuildReason": rebuild_reason,
            "integrity": integrity,
        }
        write_status(payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:
        payload = {
            "task": "host_gmail_incremental_sync",
            "stage": "error",
            "updatedAt": now_iso(),
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        write_status(payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1
    finally:
        lock.release()
        # ── Cleanup: remove temp directory to prevent disk space leak ──
        # Without this, ~370MB of temp SQLite files accumulate every cycle
        # (approximately once per minute), causing C-drive exhaustion.
        try:
            shutil.rmtree(tempdir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
