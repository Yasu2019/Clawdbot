from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "email_search.db"
RUNTIME_STATUS_PATH = ROOT / "email_rag_ingest_runtime_status.json"
DAEMON_STATUS_PATH = ROOT / "email_continuous_ingest_status.json"
BACKFILL_STATUS_PATH = ROOT / "gmail_priority_backfill_status.json"
LEARNING_SYNC_STATUS_PATH = ROOT / "email_learning_memory_sync_status.json"
LEARNING_SYNC_STATE_PATH = ROOT / "email_learning_memory_sync_state.json"
OUTPUT_PATH = ROOT / "email_ingest_dashboard_status.json"

JST = timezone(timedelta(hours=9))
WINDOW_START = "2026-01-01"


def window_bounds() -> tuple[str, str, int, int]:
    start = datetime(2026, 1, 1, tzinfo=JST)
    end_inclusive = datetime.now(JST).date() - timedelta(days=1)
    end_exclusive = datetime.combine(end_inclusive + timedelta(days=1), datetime.min.time(), tzinfo=JST)
    return (
        start.date().isoformat(),
        end_inclusive.isoformat(),
        int(start.timestamp() * 1000),
        int(end_exclusive.timestamp() * 1000),
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def age_minutes(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((datetime.now(JST).astimezone(dt.tzinfo) - dt).total_seconds() / 60.0, 1)


def sqlite_counts() -> dict[str, int]:
    if not DB_PATH.exists():
        return {}
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        window_start, window_end, window_start_ts, window_end_exclusive_ts = window_bounds()
        queries = {
            "emails_total": "select count(*) from emails",
            "tasks_total": "select count(*) from tasks",
            "emails_fts_total": "select count(*) from emails_fts",
            "tasks_fts_total": "select count(*) from tasks_fts",
            "gmail_total": "select count(*) from emails where source='gmail'",
            "eml_total": "select count(*) from emails where source='eml'",
            "gmail_2026_window": (
                "select count(*) from emails "
                "where source='gmail' and internal_ts >= ? and internal_ts < ?"
            ),
        }
        result: dict[str, int] = {}
        for key, query in queries.items():
            if "?" in query:
                result[key] = int(cur.execute(query, (window_start_ts, window_end_exclusive_ts)).fetchone()[0])
            else:
                result[key] = int(cur.execute(query).fetchone()[0])
        result["window_start"] = window_start
        result["window_end_inclusive"] = window_end
        return result
    finally:
        con.close()


def build_status() -> dict[str, Any]:
    runtime = load_json(RUNTIME_STATUS_PATH)
    daemon = load_json(DAEMON_STATUS_PATH)
    backfill = load_json(BACKFILL_STATUS_PATH)
    learning_sync = load_json(LEARNING_SYNC_STATUS_PATH)
    learning_state = load_json(LEARNING_SYNC_STATE_PATH)
    counts = sqlite_counts()
    window_start, window_end, _, _ = window_bounds()
    daemon_dt = parse_dt(daemon.get("updatedAt") or daemon.get("lastSuccessAt"))
    daemon_fresh = bool(
        daemon_dt
        and age_minutes(daemon_dt) is not None
        and age_minutes(daemon_dt) <= 20
        and daemon.get("stage") in {"idle", "indexing", "sync_learning", "dashboard_refresh", "full_backfill"}
    )
    effective_stage = daemon.get("stage") if daemon_fresh else (runtime.get("currentPhase") or runtime.get("step") or "unknown")
    effective_source = "continuous_daemon" if daemon_fresh else "legacy_runtime"
    learning_sync_dt = parse_dt(learning_sync.get("finishedAt") or learning_sync.get("startedAt") or learning_state.get("lastRunAt"))
    learning_sync_fresh = bool(
        learning_sync_dt
        and age_minutes(learning_sync_dt) is not None
        and age_minutes(learning_sync_dt) <= 60
    )
    learning_stage = learning_sync.get("stage") or "unknown"
    if daemon_fresh and daemon.get("stage") == "sync_learning":
        learning_stage = "sync_learning"
    learning_source = "continuous_daemon" if (daemon_fresh and daemon.get("stage") == "sync_learning") else ("learning_sync_status" if learning_sync_fresh else "learning_sync_state")
    learning_finished_at = (
        daemon.get("updatedAt")
        if (daemon_fresh and daemon.get("stage") == "sync_learning")
        else (learning_sync.get("finishedAt") or learning_state.get("lastRunAt"))
    )
    learning_last_run_at = (
        daemon.get("updatedAt")
        if daemon_fresh and daemon.get("stage") in {"sync_learning", "dashboard_refresh", "idle"}
        else (learning_state.get("lastRunAt") or learning_sync.get("finishedAt") or learning_sync.get("startedAt"))
    )
    learning_posted_messages = learning_sync.get("postedMessages", learning_state.get("lastPostedMessages", 0))
    learning_posted_threads = learning_sync.get("postedThreads", learning_state.get("lastPostedThreads", 0))

    rebuilt_tasks = 0
    indexed_messages = 0
    skipped_messages = 0
    errors = 0
    for chunk in (((backfill.get("result") or {}).get("summary") or {}).get("chunks") or []):
        rebuilt_tasks = max(rebuilt_tasks, int(chunk.get("rebuiltTasks") or 0))
        gmail = chunk.get("gmail") or {}
        indexed_messages += int(gmail.get("indexed") or 0)
        skipped_messages += int(gmail.get("skipped") or 0)
        errors += int(gmail.get("errors") or 0)

    return {
        "generatedAt": datetime.now().astimezone().isoformat(),
        "window": {
            "startDate": window_start,
            "endDateInclusive": window_end,
        },
        "sqlite": counts,
        "gmailBackfill": {
            "stage": daemon.get("stage") if daemon_fresh else (backfill.get("stage") or runtime.get("step") or "unknown"),
            "ok": bool(daemon_fresh or backfill.get("ok", False) or runtime.get("overall") == "ok"),
            "chunks": len(backfill.get("chunks") or []),
            "indexedMessages": indexed_messages,
            "skippedMessages": skipped_messages,
            "errors": errors,
            "rebuiltTasks": rebuilt_tasks,
            "finishedAt": daemon.get("lastSuccessAt") if daemon_fresh else (backfill.get("finishedAt") or runtime.get("finishedAt")),
        },
        "learningMemory": {
            "stage": learning_stage,
            "source": learning_source,
            "reason": learning_sync.get("reason"),
            "postedMessages": learning_posted_messages,
            "postedThreads": learning_posted_threads,
            "finishedAt": learning_finished_at,
            "lastRunAt": learning_last_run_at,
        },
        "runtime": {
            "currentPhase": effective_stage,
            "source": effective_source,
            "legacyCurrentPhase": runtime.get("currentPhase"),
            "daemonStage": daemon.get("stage"),
            "daemonUpdatedAt": daemon.get("updatedAt"),
            "daemonAgeMinutes": age_minutes(daemon_dt),
            "phase4Returncode": (((runtime.get("results") or {}).get("phase4_sqlite_search") or {}).get("returncode")),
            "phase5Returncode": (((runtime.get("results") or {}).get("phase5_learning_memory_sync") or {}).get("returncode")),
        },
    }


def main() -> None:
    OUTPUT_PATH.write_text(json.dumps(build_status(), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
