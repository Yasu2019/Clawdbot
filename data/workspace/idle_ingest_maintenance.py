#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_POSIX = SCRIPT_PATH.as_posix()
if SCRIPT_POSIX.startswith("/workspace/"):
    WORKSPACE = SCRIPT_PATH.parent
    EMAIL_CMD = "python3 /workspace/run_email_rag_ingest_report.py"
    REPORT_SYNC_CMD = "python3 /workspace/scheduled_report_search.py sync --limit-executions 20"
    CMUX_CMD = "python3 /workspace/update_cmux_status.py"
    TERMS_CMD = "python3 /workspace/update_mitsui_terms_auto.py"
elif SCRIPT_POSIX.startswith("/home/node/clawd/"):
    WORKSPACE = SCRIPT_PATH.parent
    EMAIL_CMD = "python3 /home/node/clawd/run_email_rag_ingest_report.py"
    REPORT_SYNC_CMD = "python3 /home/node/clawd/scheduled_report_search.py sync --limit-executions 20"
    CMUX_CMD = "python3 /home/node/clawd/update_cmux_status.py"
    TERMS_CMD = "python3 /home/node/clawd/update_mitsui_terms_auto.py"
else:
    WORKSPACE = SCRIPT_PATH.parents[2] / "data" / "workspace"
    EMAIL_CMD = f'python "{WORKSPACE / "run_email_rag_ingest_report.py"}"'
    REPORT_SYNC_CMD = f'python "{WORKSPACE / "scheduled_report_search.py"}" sync --limit-executions 20'
    CMUX_CMD = f'python "{WORKSPACE / "update_cmux_status.py"}"'
    TERMS_CMD = f'python "{WORKSPACE / "update_mitsui_terms_auto.py"}"'

EMAIL_RUNTIME = WORKSPACE / "email_rag_ingest_runtime_status.json"
SCHEDULED_SYNC = WORKSPACE / "scheduled_report_sync_state.json"
CMUX_STATUS = WORKSPACE / "apps" / "cmux_hub" / "cmux_status.json"
MITSUI_TERMS_STATUS = WORKSPACE / "mitsui_terms_auto_status.json"
STATUS_PATH = WORKSPACE / "idle_ingest_maintenance_status.json"
HEARTBEAT_STATE_PATH = WORKSPACE / "memory" / "heartbeat-state.json"

def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_heartbeat_state(action_names: list[str]) -> None:
    state = read_json(HEARTBEAT_STATE_PATH, {"lastChecks": {}})
    state.setdefault("lastChecks", {})
    stamp = now_jst_text()
    state["lastChecks"]["idle_ingest_maintenance"] = stamp
    for name in action_names:
        state["lastChecks"][name] = stamp
    HEARTBEAT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    candidates = [
        ("%Y-%m-%d %H:%M:%S JST", lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S JST").replace(tzinfo=JST)),
        ("%Y-%m-%dT%H:%M:%S.%f%z", lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z")),
        ("%Y-%m-%dT%H:%M:%S%z", lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z")),
    ]
    for _, parser in candidates:
        try:
            return parser(raw)
        except Exception:
            continue
    if raw.endswith("Z"):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def age_hours(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((now_jst().astimezone(dt.tzinfo) - dt).total_seconds() / 3600.0, 2)


def run_command(command: str, timeout_seconds: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": timeout_seconds,
        }


def determine_actions() -> dict[str, dict[str, Any]]:
    email = read_json(EMAIL_RUNTIME, {})
    reports = read_json(SCHEDULED_SYNC, {})
    cmux = read_json(CMUX_STATUS, {})
    mitsui_terms = read_json(MITSUI_TERMS_STATUS, {})

    email_dt = parse_dt(email.get("finishedAt") or email.get("startedAt"))
    reports_dt = parse_dt(reports.get("updatedAt") or reports.get("finishedAt"))
    cmux_dt = parse_dt(cmux.get("generatedAt"))
    terms_dt = parse_dt(mitsui_terms.get("updatedAt"))

    return {
        "email_ingest": {
            "lastSeen": email.get("finishedAt") or email.get("startedAt"),
            "ageHours": age_hours(email_dt),
            "shouldRun": email_dt is None or (now_jst().astimezone(email_dt.tzinfo) - email_dt) >= timedelta(hours=8),
            "reason": "stale_or_missing" if (email_dt is None or (now_jst().astimezone(email_dt.tzinfo) - email_dt) >= timedelta(hours=8)) else "fresh",
        },
        "scheduled_reports_sync": {
            "lastSeen": reports.get("updatedAt") or reports.get("finishedAt"),
            "ageHours": age_hours(reports_dt),
            "shouldRun": reports_dt is None or (now_jst().astimezone(reports_dt.tzinfo) - reports_dt) >= timedelta(hours=2),
            "reason": "stale_or_missing" if (reports_dt is None or (now_jst().astimezone(reports_dt.tzinfo) - reports_dt) >= timedelta(hours=2)) else "fresh",
        },
        "cmux_status_refresh": {
            "lastSeen": cmux.get("generatedAt"),
            "ageHours": age_hours(cmux_dt),
            "shouldRun": cmux_dt is None or (now_jst().astimezone(cmux_dt.tzinfo) - cmux_dt) >= timedelta(hours=1),
            "reason": "stale_or_missing" if (cmux_dt is None or (now_jst().astimezone(cmux_dt.tzinfo) - cmux_dt) >= timedelta(hours=1)) else "fresh",
        },
        "mitsui_terms_refresh": {
            "lastSeen": mitsui_terms.get("updatedAt"),
            "ageHours": age_hours(terms_dt),
            "shouldRun": terms_dt is None or (now_jst().astimezone(terms_dt.tzinfo) - terms_dt) >= timedelta(hours=24),
            "reason": "stale_or_missing" if (terms_dt is None or (now_jst().astimezone(terms_dt.tzinfo) - terms_dt) >= timedelta(hours=24)) else "fresh",
        },
    }


def main() -> None:
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "step": "evaluate",
        "actions": determine_actions(),
        "results": {},
    }
    write_status(status)

    if status["actions"]["email_ingest"]["shouldRun"]:
        status["step"] = "email_ingest"
        write_status(status)
        status["results"]["email_ingest"] = run_command(EMAIL_CMD, 1800)
        write_status(status)

    if status["actions"]["scheduled_reports_sync"]["shouldRun"]:
        status["step"] = "scheduled_reports_sync"
        write_status(status)
        status["results"]["scheduled_reports_sync"] = run_command(REPORT_SYNC_CMD, 300)
        write_status(status)

    if status["actions"]["cmux_status_refresh"]["shouldRun"]:
        status["step"] = "cmux_status_refresh"
        write_status(status)
        status["results"]["cmux_status_refresh"] = run_command(CMUX_CMD, 120)
        write_status(status)

    if status["actions"]["mitsui_terms_refresh"]["shouldRun"]:
        status["step"] = "mitsui_terms_refresh"
        write_status(status)
        status["results"]["mitsui_terms_refresh"] = run_command(TERMS_CMD, 180)
        write_status(status)

    update_heartbeat_state(list(status["results"].keys()))
    status["step"] = "completed"
    status["finishedAt"] = now_jst_text()
    write_status(status)


if __name__ == "__main__":
    main()
