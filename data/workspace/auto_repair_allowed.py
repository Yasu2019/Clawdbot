#!/usr/bin/env python3
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
def resolve_repo_root() -> Path:
    # 1. Traversal from WORKSPACE (Most reliable if __file__ is accurate)
    curr = WORKSPACE
    for _ in range(5):
        if (curr / ".env").exists() and (curr / "docker-compose.yml").exists():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent

    # 2. Historical fallback
    candidate = WORKSPACE.parent.parent
    if candidate.exists() and (candidate / ".env").exists():
        return candidate

    # 3. Current Working Directory
    if (Path.cwd() / ".env").exists() and (Path.cwd() / "docker-compose.yml").exists():
        return Path.cwd()

    # 4. Emergency fallback for this specific environment
    mini_pc_root = Path("D:/Clawdbot_Docker_20260125")
    if mini_pc_root.exists():
        return mini_pc_root

    return Path.cwd()


ROOT = resolve_repo_root()
print(f"[auto_repair] Resolved ROOT to: {ROOT}")
STATUS_PATH = WORKSPACE / "auto_repair_allowed_status.json"
STATE_PATH = WORKSPACE / "auto_repair_allowed_state.json"
EMAIL_RUNTIME = WORKSPACE / "email_rag_ingest_runtime_status.json"
EMAIL_DAEMON_STATUS = WORKSPACE / "email_continuous_ingest_status.json"
CAE_SYNC_STATUS = WORKSPACE / "cae_learning_memory_sync_status.json"
MAINTENANCE_MODE_PATH = WORKSPACE / "maintenance_mode.json"

SCHEDULED_REPORT_STATUS = WORKSPACE / "scheduled_report_search_status.json"
IDLE_MAINTENANCE_STATUS = WORKSPACE / "idle_ingest_maintenance_status.json"
EMAIL_WATCHDOG_START = ROOT / "scripts" / "start_email_continuous_watchdog.ps1"
LEARNING_REPAIR_SCRIPT = WORKSPACE / "repair_learning_engine.py"
PAPERLESS_RAG_WATCHDOG_STATUS = WORKSPACE / "paperless_rag_watchdog_status.json"
PAPERLESS_INGEST_STATUS = WORKSPACE / "ingest_watchdog_status.json"
PAPERLESS_INGEST_CONFIG = WORKSPACE / "paperless_ingest_config.json"
PAPERLESS_TOKEN_REFRESH_SCRIPT = WORKSPACE / "refresh_paperless_ingest_token.py"
PAPERLESS_RAG_WATCHDOG_START = ROOT / "scripts" / "start_paperless_rag_watchdog.ps1"
CLAUDIAN_WATCHDOG_STATUS = WORKSPACE / "claudian_watchdog_status.json"
DOCKER_UI_WATCHDOG_STATUS = WORKSPACE / "docker_desktop_ui_watchdog_status.json"
MINIPC_OPTIMIZER_WATCHDOG_STATUS = WORKSPACE / "minipc_optimizer_watchdog_status.json"
EMAIL_BLACKLIST_HUB_STATUS = WORKSPACE / "email_blacklist_hub_status.json"
EMAIL_SEARCH_API_PID = WORKSPACE / "email_search_api_windows.pid"
API_COST_REPORT_STATUS = WORKSPACE / "api_cost_report_status.json"
SELF_GROWTH_STATUS = WORKSPACE / "agent_self_growth_memory_hygiene_status.json"
SELF_GROWTH_HARNESS_STATUS = ROOT / "data" / "state" / "agent_self_growth_memory_hygiene" / "harness_status.json"
PDCA_STATUS = WORKSPACE / "pdca_lab" / "state" / "status.json"
CLAUDIAN_WATCHDOG_START = ROOT / "scripts" / "start_claudian_watchdog.ps1"
DOCKER_UI_WATCHDOG_START = ROOT / "scripts" / "start_docker_desktop_ui_watchdog.ps1"
MINIPC_OPTIMIZER_WATCHDOG_START = ROOT / "scripts" / "start_minipc_optimizer_watchdog.ps1"
EMAIL_BLACKLIST_HUB_START = ROOT / "scripts" / "start_email_blacklist_hub_api.ps1"
EMAIL_SEARCH_API_START = ROOT / "scripts" / "start_email_search_api.ps1"
API_COST_REPORT_START = ROOT / "scripts" / "run_api_cost_report.ps1"
SELF_GROWTH_START = ROOT / "scripts" / "start_agent_self_growth_memory_hygiene.ps1"
PDCA_REFRESH_START = ROOT / "scripts" / "run_pdca_feedback_refresh.ps1"

EMAIL_CMD = f'python "{WORKSPACE / "run_email_rag_ingest_report.py"}"'
EMAIL_DAEMON_CMD = (
    f'python3 "{WORKSPACE / "continuous_email_ingest_daemon.py"}" '
    '--poll-seconds 300 --learning-interval-cycles 3 --full-backfill-interval-cycles 72'
)
CAE_CMD = f'python "{WORKSPACE / "sync_cae_learning_memory.py"}" --base-url "http://localhost:8110" --source-org "Mitsui"'
REPORT_CMD = ["python", str(WORKSPACE / "scheduled_report_search.py"), "sync", "--limit-executions", "20"]

LEARNING_REPAIR_CMD = f'python3 "{LEARNING_REPAIR_SCRIPT}"'
PAPERLESS_RAG_WATCHDOG_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PAPERLESS_RAG_WATCHDOG_START)]

PAPERLESS_TOKEN_REFRESH_CMD = f'python3 "{PAPERLESS_TOKEN_REFRESH_SCRIPT}"'
CLAUDIAN_WATCHDOG_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(CLAUDIAN_WATCHDOG_START)]

DOCKER_UI_WATCHDOG_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(DOCKER_UI_WATCHDOG_START)]

MINIPC_OPTIMIZER_WATCHDOG_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(MINIPC_OPTIMIZER_WATCHDOG_START)]

EMAIL_BLACKLIST_HUB_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(EMAIL_BLACKLIST_HUB_START)]

EMAIL_SEARCH_API_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(EMAIL_SEARCH_API_START)]
API_COST_REPORT_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(API_COST_REPORT_START)]
SELF_GROWTH_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SELF_GROWTH_START)]
PDCA_REFRESH_CMD = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PDCA_REFRESH_START)]

EMAIL_SEARCH_STATS_URL = "http://127.0.0.1:8792/api/stats"


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


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def run_command(command: str | list[str], timeout_seconds: int) -> dict[str, Any]:
    try:
        shell = isinstance(command, str)
        proc = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            # CMD窓の点滅防止(2026-07-13): CREATE_NO_WINDOW(Windows以外は0)
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": timeout_seconds,
        }
    except Exception as exc:
        return {
            "command": command if isinstance(command, str) else " ".join(command),
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "timedOut": False,
        }


def ps_contains(token: str) -> bool:
    cmd = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "Select-Object -First 1 ProcessId | ConvertTo-Json -Compress"
    )
    result = run_command(f'powershell -NoProfile -Command "{cmd}"', 30)
    return bool(result.get("stdout") and "ProcessId" in result["stdout"])


def can_attempt(state: dict[str, Any], key: str, max_attempts: int = 3, window_minutes: int = 60) -> tuple[bool, dict[str, Any]]:
    attempts = state.setdefault("attempts", {}).setdefault(key, [])
    now = now_jst()
    recent: list[str] = []
    for stamp in attempts:
        dt = parse_dt(stamp)
        if dt and (now.astimezone(dt.tzinfo) - dt) < timedelta(minutes=window_minutes):
            recent.append(stamp)
    state["attempts"][key] = recent
    if len(recent) >= max_attempts:
        return False, {
            "skipped": True,
            "reason": f"cooldown active after {len(recent)} attempts within {window_minutes} minutes",
        }
    recent.append(now_jst_text())
    state["attempts"][key] = recent
    return True, {}


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


def should_repair_email_daemon(daemon_status: dict[str, Any]) -> tuple[bool, str]:
    updated = parse_dt(daemon_status.get("updatedAt") or daemon_status.get("lastSuccessAt"))
    stage = str(daemon_status.get("stage") or "")
    if updated is None:
        return True, "daemon status missing"
    if (now_jst().astimezone(updated.tzinfo) - updated) >= timedelta(minutes=15):
        return True, "daemon heartbeat stale"
    if stage == "error":
        return True, "daemon entered error state"
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


def should_repair_learning_engine(cae_status: dict[str, Any]) -> tuple[bool, str]:
    reason = str(cae_status.get("reason") or "")
    if "learning_engine unavailable" in reason.lower():
        return True, "cae sync observed learning_engine unavailable"
    return False, "healthy"


def should_repair_paperless_rag(watchdog_status: dict[str, Any], ingest_status: dict[str, Any]) -> tuple[bool, str]:
    if not ps_contains("paperless_rag_watchdog.py"):
        return True, "paperless watchdog process missing"
    watchdog_updated = parse_dt(watchdog_status.get("updatedAt"))
    ingest_updated = parse_dt(ingest_status.get("updatedAt"))
    ingest_stage = str(ingest_status.get("stage") or "")
    if watchdog_updated is None:
        return True, "paperless watchdog status missing"
    if (now_jst().astimezone(watchdog_updated.tzinfo) - watchdog_updated) >= timedelta(minutes=20):
        return True, "paperless watchdog stale"
    if ingest_updated is None:
        return True, "paperless ingest heartbeat missing"
    if (now_jst().astimezone(ingest_updated.tzinfo) - ingest_updated) >= timedelta(minutes=20):
        return True, "paperless ingest heartbeat stale"
    if ingest_stage == "error":
        return True, "paperless ingest reported error state"
    return False, "healthy"


def load_paperless_ingest_config() -> dict[str, Any]:
    return read_json(PAPERLESS_INGEST_CONFIG)


def should_refresh_paperless_token() -> tuple[bool, str]:
    config = load_paperless_ingest_config()
    token = str(config.get("paperlessToken") or "").strip()
    base_url = str(config.get("paperlessUrl") or "http://host.docker.internal:8000").strip()
    if not token:
        return True, "paperless token missing"
    probe_urls = [base_url]
    if "://host.docker.internal:" in base_url:
        probe_urls.append(base_url.replace("://host.docker.internal:", "://127.0.0.1:"))
        probe_urls.append(base_url.replace("://host.docker.internal:", "://localhost:"))
    for probe_url in probe_urls:
        try:
            resp = requests.get(
                f"{probe_url.rstrip('/')}/api/documents/?page_size=1",
                headers={"Authorization": f"Token {token}"},
                timeout=8,
            )
            if resp.status_code in {401, 403}:
                return True, f"paperless auth returned {resp.status_code}"
            if resp.ok:
                return False, "healthy"
        except Exception:
            continue
    return False, "probe inconclusive"


def should_restart_watchdog(status_payload: dict[str, Any], process_token: str, max_age_minutes: int) -> tuple[bool, str]:
    updated = parse_dt(status_payload.get("updatedAt") or status_payload.get("startedAt"))
    if not ps_contains(process_token):
        return True, f"{process_token} process missing"
    if updated is None:
        return True, f"{process_token} status missing"
    if (now_jst().astimezone(updated.tzinfo) - updated) >= timedelta(minutes=max_age_minutes):
        return True, f"{process_token} status stale"
    return False, "healthy"


def should_repair_email_search_api() -> tuple[bool, str]:
    if not ps_contains("email_search_api.py"):
        return True, "email_search_api.py process missing"
    try:
        resp = requests.get(EMAIL_SEARCH_STATS_URL, timeout=8)
        if not resp.ok:
            return True, f"email search api returned {resp.status_code}"
    except Exception as exc:
        return True, f"email search api probe failed: {exc}"
    return False, "healthy"


def payload_age_minutes(payload: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        updated = parse_dt(payload.get(key))
        if updated is not None:
            return age_minutes(updated)
    return None


def should_run_api_cost_report(payload: dict[str, Any]) -> tuple[bool, str]:
    if not payload:
        return True, "P009 status missing"
    if payload.get("status") not in {"active", "success", "ok"}:
        return True, f"P009 status is {payload.get('status')}"
    age = payload_age_minutes(payload, ["generated_at_jst", "updatedAt", "startedAt"])
    if age is None:
        return True, "P009 timestamp missing"
    if age >= 720:
        return True, f"P009 report stale: ageMinutes={age}"
    return False, f"healthy: ageMinutes={age}"


def should_restart_self_growth_hygiene(status_payload: dict[str, Any], harness_payload: dict[str, Any]) -> tuple[bool, str]:
    if not ps_contains("agent_self_growth_memory_hygiene.py"):
        return True, "agent_self_growth_memory_hygiene.py process missing"
    age = payload_age_minutes(status_payload, ["updatedAt", "startedAt"])
    harness_age = payload_age_minutes(harness_payload, ["updatedAt"])
    ages = [item for item in [age, harness_age] if item is not None]
    best_age = min(ages) if ages else None
    if best_age is None:
        return True, "self-growth hygiene timestamp missing"
    if best_age >= 390:
        return True, f"self-growth hygiene stale: ageMinutes={best_age}"
    return False, f"healthy: ageMinutes={best_age}"


def should_refresh_pdca_status(payload: dict[str, Any]) -> tuple[bool, str]:
    if not payload:
        return True, "PDCA status missing"
    age = payload_age_minutes(payload, ["updatedAt", "created_at", "startedAt"])
    if age is None:
        return True, "PDCA timestamp missing"
    if age >= 180:
        return True, f"PDCA refresh stale: ageMinutes={age}"
    return False, f"healthy: ageMinutes={age}"


def classify_repair_reason(reason: str) -> dict[str, str]:
    lowered = reason.lower()
    if "missing" in lowered:
        cause = "missing_status_or_process"
        countermeasure = "start_or_regenerate_status"
    elif "stale" in lowered:
        cause = "stale_status"
        countermeasure = "refresh_status_or_restart_worker"
    elif "status is" in lowered:
        cause = "unexpected_status"
        countermeasure = "rerun_component_and_verify_status"
    else:
        cause = "freshness_probe_failed"
        countermeasure = "rerun_component_and_recheck"
    return {"cause": cause, "countermeasure": countermeasure}


def run_cause_aware_repair(
    *,
    status: dict[str, Any],
    repair_state: dict[str, Any],
    key: str,
    reason: str,
    command: list[str],
    timeout_seconds: int,
    verify: Any,
    max_attempts: int = 3,
    window_minutes: int = 180,
) -> None:
    status["results"].setdefault(key, {"attempts": []})
    for _ in range(max_attempts):
        still_needed, verify_reason = verify()
        if not still_needed:
            status["results"][key]["status"] = "success"
            status["results"][key]["verification"] = verify_reason
            write_status(status)
            return

        allowed, gate = can_attempt(repair_state, key, max_attempts=max_attempts, window_minutes=window_minutes)
        attempt_no = len(status["results"][key]["attempts"]) + 1
        diagnosis = classify_repair_reason(verify_reason or reason)
        attempt_record: dict[str, Any] = {
            "attempt": attempt_no,
            "diagnosis": diagnosis,
            "reason_before": verify_reason or reason,
            "command": " ".join(command),
        }
        if not allowed:
            attempt_record["skipped"] = True
            attempt_record["gate"] = gate
            status["results"][key]["attempts"].append(attempt_record)
            status["results"][key]["status"] = "deferred_by_p015_gate"
            write_status(status)
            return

        attempt_record["result"] = run_command(command, timeout_seconds)
        after_needed, after_reason = verify()
        attempt_record["reason_after"] = after_reason
        attempt_record["verified"] = not after_needed
        status["results"][key]["attempts"].append(attempt_record)
        write_status(status)
        if not after_needed:
            status["results"][key]["status"] = "success"
            status["results"][key]["verification"] = after_reason
            write_status(status)
            return

    status["results"][key]["status"] = "failed_after_diagnosed_3_attempts"
    write_status(status)


def main() -> None:
    email_status = read_json(EMAIL_RUNTIME)
    email_daemon_status = read_json(EMAIL_DAEMON_STATUS)
    cae_status = read_json(CAE_SYNC_STATUS)
    report_status = read_json(SCHEDULED_REPORT_STATUS)
    idle_status = read_json(IDLE_MAINTENANCE_STATUS)
    paperless_watchdog_status = read_json(PAPERLESS_RAG_WATCHDOG_STATUS)
    paperless_ingest_status = read_json(PAPERLESS_INGEST_STATUS)
    claudian_watchdog_status = read_json(CLAUDIAN_WATCHDOG_STATUS)
    docker_ui_watchdog_status = read_json(DOCKER_UI_WATCHDOG_STATUS)
    minipc_optimizer_watchdog_status = read_json(MINIPC_OPTIMIZER_WATCHDOG_STATUS)
    email_blacklist_hub_status = read_json(EMAIL_BLACKLIST_HUB_STATUS)
    api_cost_report_status = read_json(API_COST_REPORT_STATUS)
    self_growth_status = read_json(SELF_GROWTH_STATUS)
    self_growth_harness_status = read_json(SELF_GROWTH_HARNESS_STATUS)
    pdca_status = read_json(PDCA_STATUS)
    repair_state = read_json(STATE_PATH)
    maintenance = read_json(MAINTENANCE_MODE_PATH)
    excluded = set(maintenance.get("excluded_services") or [])



    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "step": "evaluate",
        "rules": [],
        "actions": [],
        "results": {},
    }

    email_daemon_fix, email_daemon_reason = should_repair_email_daemon(email_daemon_status)
    email_fix, email_reason = should_repair_email_runtime(email_status)
    cae_fix, cae_reason = should_repair_cae_status(cae_status)
    report_fix, report_reason = should_repair_scheduled_reports(report_status, idle_status)
    learning_fix, learning_reason = should_repair_learning_engine(cae_status)
    paperless_fix, paperless_reason = should_repair_paperless_rag(paperless_watchdog_status, paperless_ingest_status)
    paperless_token_fix, paperless_token_reason = should_refresh_paperless_token()
    claudian_fix, claudian_reason = should_restart_watchdog(claudian_watchdog_status, "claudian_watchdog.py", 30)
    docker_ui_fix, docker_ui_reason = should_restart_watchdog(docker_ui_watchdog_status, "docker_desktop_ui_watchdog.py", 30)
    minipc_fix, minipc_reason = should_restart_watchdog(minipc_optimizer_watchdog_status, "minipc_optimizer_watchdog.py", 30)
    blacklist_fix, blacklist_reason = should_restart_watchdog(email_blacklist_hub_status, "email_blacklist_hub_api.py", 180)
    email_search_fix, email_search_reason = should_repair_email_search_api()
    p009_fix, p009_reason = should_run_api_cost_report(api_cost_report_status)
    self_growth_fix, self_growth_reason = should_restart_self_growth_hygiene(self_growth_status, self_growth_harness_status)
    pdca_fix, pdca_reason = should_refresh_pdca_status(pdca_status)
    if report_fix and email_runtime_in_progress(email_status):
        report_fix = False
        report_reason = "email nightly in progress; defer scheduled report repair"

    status["rules"].append({"name": "email_daemon", "shouldRepair": email_daemon_fix, "reason": email_daemon_reason})
    status["rules"].append({"name": "email_runtime", "shouldRepair": email_fix, "reason": email_reason})
    status["rules"].append({"name": "cae_sync", "shouldRepair": cae_fix, "reason": cae_reason})
    status["rules"].append({"name": "scheduled_reports", "shouldRepair": report_fix, "reason": report_reason})
    status["rules"].append({"name": "learning_engine", "shouldRepair": learning_fix, "reason": learning_reason})
    status["rules"].append({"name": "paperless_rag", "shouldRepair": paperless_fix, "reason": paperless_reason})
    status["rules"].append({"name": "paperless_token", "shouldRepair": paperless_token_fix, "reason": paperless_token_reason})
    status["rules"].append({"name": "claudian_watchdog", "shouldRepair": claudian_fix, "reason": claudian_reason})
    status["rules"].append({"name": "docker_ui_watchdog", "shouldRepair": docker_ui_fix, "reason": docker_ui_reason})
    status["rules"].append({"name": "minipc_optimizer_watchdog", "shouldRepair": minipc_fix, "reason": minipc_reason})
    status["rules"].append({"name": "email_blacklist_hub", "shouldRepair": blacklist_fix, "reason": blacklist_reason})
    status["rules"].append({"name": "email_search_api", "shouldRepair": email_search_fix, "reason": email_search_reason})
    status["rules"].append({"name": "p009_api_cost_report", "shouldRepair": p009_fix, "reason": p009_reason})
    status["rules"].append({"name": "agent_self_growth_memory_hygiene", "shouldRepair": self_growth_fix, "reason": self_growth_reason})
    status["rules"].append({"name": "pdca_feedback_refresh", "shouldRepair": pdca_fix, "reason": pdca_reason})

    for rule in status["rules"]:
        if rule["name"] in excluded:
            rule["shouldRepair"] = False
            rule["reason"] = f"planned_maintenance (via {MAINTENANCE_MODE_PATH.name})"

    write_status(status)


    if learning_fix:
        status["step"] = "repair_learning_engine"
        status["actions"].append("learning_engine_repair")
        write_status(status)

    if paperless_fix:
        status["step"] = "repair_paperless_rag"
        status["actions"].append("paperless_rag_watchdog_restart")
        write_status(status)
        if paperless_token_fix:
            allowed, result = can_attempt(repair_state, "paperless_token_refresh", max_attempts=3, window_minutes=180)
            if allowed:
                status["results"]["paperless_token_refresh"] = run_command(PAPERLESS_TOKEN_REFRESH_CMD, 120)
            else:
                status["results"]["paperless_token_refresh"] = result
            write_status(status)
        allowed, result = can_attempt(repair_state, "paperless_rag_watchdog_restart", max_attempts=3, window_minutes=120)
        if allowed:
            status["results"]["paperless_rag_watchdog_restart"] = run_command(PAPERLESS_RAG_WATCHDOG_CMD, 120)
        else:
            status["results"]["paperless_rag_watchdog_restart"] = result
        write_status(status)
        allowed, result = can_attempt(repair_state, "learning_engine_repair", max_attempts=2, window_minutes=120)
        if allowed:
            status["results"]["learning_engine_repair"] = run_command(LEARNING_REPAIR_CMD, 900)
        else:
            status["results"]["learning_engine_repair"] = result
        write_status(status)
    elif paperless_token_fix:
        status["step"] = "refresh_paperless_token"
        status["actions"].append("paperless_token_refresh")
        write_status(status)
        allowed, result = can_attempt(repair_state, "paperless_token_refresh", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["paperless_token_refresh"] = run_command(PAPERLESS_TOKEN_REFRESH_CMD, 120)
        else:
            status["results"]["paperless_token_refresh"] = result
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

    if email_daemon_fix and not ps_contains("continuous_email_ingest_daemon.py"):
        status["step"] = "repair_email_daemon"
        status["actions"].append("email_daemon_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "email_daemon_restart")
        if allowed:
            status["results"]["email_daemon_restart"] = run_command(
                f'powershell -NoProfile -ExecutionPolicy Bypass -File "{EMAIL_WATCHDOG_START}"',
                60,
            )
        else:
            status["results"]["email_daemon_restart"] = result
        write_status(status)
    elif email_daemon_fix:
        status["results"]["email_daemon_restart"] = {
            "skipped": True,
            "reason": "continuous_email_ingest_daemon.py already running",
        }
        write_status(status)

    if email_fix and not ps_contains("run_email_rag_ingest_report.py"):
        status["step"] = "repair_email_runtime"
        status["actions"].append("email_ingest_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "email_ingest_restart")
        if allowed:
            status["results"]["email_ingest_restart"] = run_command(
                f'powershell -NoProfile -Command "Start-Process -FilePath python3 -ArgumentList \'{WORKSPACE / "run_email_rag_ingest_report.py"}\' -WindowStyle Hidden"',
                60,
            )
        else:
            status["results"]["email_ingest_restart"] = result
        write_status(status)
    elif email_fix:
        status["results"]["email_ingest_restart"] = {
            "skipped": True,
            "reason": "run_email_rag_ingest_report.py already running",
        }
        write_status(status)

    if claudian_fix:
        status["step"] = "repair_claudian_watchdog"
        status["actions"].append("claudian_watchdog_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "claudian_watchdog_restart", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["claudian_watchdog_restart"] = run_command(CLAUDIAN_WATCHDOG_CMD, 60)
        else:
            status["results"]["claudian_watchdog_restart"] = result
        write_status(status)

    if docker_ui_fix:
        status["step"] = "repair_docker_ui_watchdog"
        status["actions"].append("docker_ui_watchdog_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "docker_ui_watchdog_restart", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["docker_ui_watchdog_restart"] = run_command(DOCKER_UI_WATCHDOG_CMD, 60)
        else:
            status["results"]["docker_ui_watchdog_restart"] = result
        write_status(status)

    if minipc_fix:
        status["step"] = "repair_minipc_optimizer_watchdog"
        status["actions"].append("minipc_optimizer_watchdog_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "minipc_optimizer_watchdog_restart", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["minipc_optimizer_watchdog_restart"] = run_command(MINIPC_OPTIMIZER_WATCHDOG_CMD, 60)
        else:
            status["results"]["minipc_optimizer_watchdog_restart"] = result
        write_status(status)

    if blacklist_fix:
        status["step"] = "repair_email_blacklist_hub"
        status["actions"].append("email_blacklist_hub_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "email_blacklist_hub_restart", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["email_blacklist_hub_restart"] = run_command(EMAIL_BLACKLIST_HUB_CMD, 60)
        else:
            status["results"]["email_blacklist_hub_restart"] = result
        write_status(status)

    if email_search_fix:
        status["step"] = "repair_email_search_api"
        status["actions"].append("email_search_api_restart")
        write_status(status)
        allowed, result = can_attempt(repair_state, "email_search_api_restart", max_attempts=3, window_minutes=180)
        if allowed:
            status["results"]["email_search_api_restart"] = run_command(EMAIL_SEARCH_API_CMD, 60)
        else:
            status["results"]["email_search_api_restart"] = result
        write_status(status)

    if p009_fix:
        status["step"] = "repair_p009_api_cost_report"
        status["actions"].append("p009_api_cost_report_run")
        write_status(status)
        run_cause_aware_repair(
            status=status,
            repair_state=repair_state,
            key="p009_api_cost_report_run",
            reason=p009_reason,
            command=API_COST_REPORT_CMD,
            timeout_seconds=180,
            verify=lambda: should_run_api_cost_report(read_json(API_COST_REPORT_STATUS)),
        )

    if self_growth_fix:
        status["step"] = "repair_agent_self_growth_memory_hygiene"
        status["actions"].append("agent_self_growth_memory_hygiene_restart")
        write_status(status)
        run_cause_aware_repair(
            status=status,
            repair_state=repair_state,
            key="agent_self_growth_memory_hygiene_restart",
            reason=self_growth_reason,
            command=SELF_GROWTH_CMD,
            timeout_seconds=90,
            verify=lambda: should_restart_self_growth_hygiene(read_json(SELF_GROWTH_STATUS), read_json(SELF_GROWTH_HARNESS_STATUS)),
        )

    if pdca_fix:
        status["step"] = "repair_pdca_feedback_refresh"
        status["actions"].append("pdca_feedback_refresh")
        write_status(status)
        run_cause_aware_repair(
            status=status,
            repair_state=repair_state,
            key="pdca_feedback_refresh",
            reason=pdca_reason,
            command=PDCA_REFRESH_CMD,
            timeout_seconds=120,
            verify=lambda: should_refresh_pdca_status(read_json(PDCA_STATUS)),
        )

    status["step"] = "completed"
    status["finishedAt"] = now_jst_text()
    write_status(status)
    save_json(STATE_PATH, repair_state)


if __name__ == "__main__":
    main()
