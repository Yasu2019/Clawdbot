#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
STATUS_PATH = WORKSPACE / "auto_repair_allowed_status.json"
EMAIL_RUNTIME = WORKSPACE / "email_rag_ingest_runtime_status.json"
CAE_SYNC_STATUS = WORKSPACE / "cae_learning_memory_sync_status.json"
SCHEDULED_REPORT_STATUS = WORKSPACE / "scheduled_report_search_status.json"
IDLE_MAINTENANCE_STATUS = WORKSPACE / "idle_ingest_maintenance_status.json"

EMAIL_CMD = f'python "{WORKSPACE / "run_email_rag_ingest_report.py"}"'
CAE_CMD = f'python "{WORKSPACE / "sync_cae_learning_memory.py"}" --base-url "http://localhost:8110" --source-org "Mitsui"'
REPORT_CMD = 'docker exec clawstack-unified-learning_engine-1 python3 /workspace/scheduled_report_search.py sync --limit-executions 20'


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
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
    patterns = [
        ("%Y-%m-%d %H:%M:%S JST", lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S JST").replace(tzinfo=JST)),
        ("%Y-%m-%dT%H:%M:%S.%f%z", lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z")),
        ("%Y-%m-%dT%H:%M:%S%z", lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z")),
    ]
    for _, parser in patterns:
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


def age_minutes(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((now_jst().astimezone(dt.tzinfo) - dt).total_seconds() / 60.0, 1)


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


def ps_contains(token: str) -> bool:
    cmd = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "Select-Object -First 1 ProcessId | ConvertTo-Json -Compress"
    )
    result = run_command(f'powershell -NoProfile -Command "{cmd}"', 30)
    return bool(result.get("stdout") and "ProcessId" in result["stdout"])


def should_repair_email_runtime(email_status: dict[str, Any]) -> tuple[bool, str]:
    started = parse_dt(email_status.get("startedAt"))
    current_phase = email_status.get("currentPhase")
    step = email_status.get("step")
    results = email_status.get("results") or {}
    timed_out = any((result or {}).get("timedOut") for result in results.values() if isinstance(result, dict))
    if timed_out:
        return True, "timedOut phase detected"
    if step != "completed" and started and (now_jst().astimezone(started.tzinfo) - started) >= timedelta(hours=2):
        return True, f"runtime stuck at {current_phase or step}"
    return False, "healthy"


def email_runtime_in_progress(email_status: dict[str, Any]) -> bool:
    step = email_status.get("step")
    started = parse_dt(email_status.get("startedAt"))
    if step == "completed":
      return False
    if started and (now_jst().astimezone(started.tzinfo) - started) < timedelta(hours=6):
      return True
    return False


def should_repair_cae_status(cae_status: dict[str, Any]) -> tuple[bool, str]:
    stage = cae_status.get("stage")
    reason = str(cae_status.get("reason") or "")
    finished = parse_dt(cae_status.get("finishedAt") or cae_status.get("startedAt"))
    if stage == "skipped" and "learning_engine unavailable" in reason.lower():
        return True, "cae sync skipped due to learning_engine unavailable"
    if stage not in {"completed", "loaded", "posting"} and finished and (now_jst().astimezone(finished.tzinfo) - finished) >= timedelta(hours=12):
        return True, "cae sync stale"
    return False, "healthy"


def should_repair_scheduled_reports(report_status: dict[str, Any], idle_status: dict[str, Any]) -> tuple[bool, str]:
    updated = parse_dt(report_status.get("updatedAt"))
    idle_result = ((idle_status.get("results") or {}).get("scheduled_reports_sync") or {})
    if idle_result.get("timedOut"):
        return True, "scheduled report sync timed out"
    if idle_result.get("returncode") not in (None, 0):
        return True, "scheduled report sync returned non-zero"
    if updated is None or (now_jst().astimezone(updated.tzinfo) - updated) >= timedelta(hours=4):
        return True, "scheduled report sync stale"
    return False, "healthy"


def main() -> None:
    email_status = read_json(EMAIL_RUNTIME)
    cae_status = read_json(CAE_SYNC_STATUS)
    report_status = read_json(SCHEDULED_REPORT_STATUS)
    idle_status = read_json(IDLE_MAINTENANCE_STATUS)

    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "step": "evaluate",
        "rules": [],
        "actions": [],
        "results": {},
    }

    email_fix, email_reason = should_repair_email_runtime(email_status)
    cae_fix, cae_reason = should_repair_cae_status(cae_status)
    report_fix, report_reason = should_repair_scheduled_reports(report_status, idle_status)
    if report_fix and email_runtime_in_progress(email_status):
        report_fix = False
        report_reason = "email nightly in progress; defer scheduled report repair"

    status["rules"].append({"name": "email_runtime", "shouldRepair": email_fix, "reason": email_reason})
    status["rules"].append({"name": "cae_sync", "shouldRepair": cae_fix, "reason": cae_reason})
    status["rules"].append({"name": "scheduled_reports", "shouldRepair": report_fix, "reason": report_reason})
    write_status(status)

    if report_fix:
        status["step"] = "repair_scheduled_reports"
        status["actions"].append("scheduled_reports_sync")
        write_status(status)
        status["results"]["scheduled_reports_sync"] = run_command(REPORT_CMD, 300)
        write_status(status)

    if cae_fix:
        status["step"] = "repair_cae_sync"
        status["actions"].append("cae_learning_sync")
        write_status(status)
        status["results"]["cae_learning_sync"] = run_command(CAE_CMD, 300)
        write_status(status)

    if email_fix and not ps_contains("run_email_rag_ingest_report.py"):
        status["step"] = "repair_email_runtime"
        status["actions"].append("email_ingest_restart")
        write_status(status)
        status["results"]["email_ingest_restart"] = run_command(
            f'powershell -NoProfile -Command "Start-Process -FilePath python -ArgumentList \'{WORKSPACE / "run_email_rag_ingest_report.py"}\' -WindowStyle Hidden"',
            60,
        )
        write_status(status)
    elif email_fix:
        status["results"]["email_ingest_restart"] = {
            "skipped": True,
            "reason": "run_email_rag_ingest_report.py already running",
        }
        write_status(status)

    status["step"] = "completed"
    status["finishedAt"] = now_jst_text()
    write_status(status)


if __name__ == "__main__":
    main()
