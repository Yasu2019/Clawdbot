#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent


def resolve_repo_root() -> Path:
    candidates = [
        WORKSPACE.parent.parent,
        Path.cwd(),
    ]
    for candidate in candidates:
        if (candidate / "scripts").exists() and (candidate / "docs").exists():
            return candidate
    return Path.cwd()


ROOT = resolve_repo_root()

STATUS_PATH = WORKSPACE / "continuous_system_improvement_status.json"
STATE_PATH = WORKSPACE / "continuous_system_improvement_state.json"
SUMMARY_PATH = WORKSPACE / "continuous_system_improvement_summary.md"

EMAIL_WATCHDOG_STATUS = WORKSPACE / "email_continuous_watchdog_status.json"
EMAIL_DAEMON_STATUS = WORKSPACE / "email_continuous_ingest_status.json"
IDLE_STATUS = WORKSPACE / "idle_ingest_maintenance_status.json"
AUTO_REPAIR_STATUS = WORKSPACE / "auto_repair_allowed_status.json"
RISK_NOTIFICATION_STATUS = WORKSPACE / "risk_notification_status.json"
EMAIL_QUALITY_STATUS = WORKSPACE / "email_request_quality_status.json"
EMAIL_POLICY_PATH = WORKSPACE / "email_ops_policy.json"
OUTBOUND_GUARD_STATUS_PATH = WORKSPACE / "outbound_delivery_guard_status.json"
EMAIL_INTEGRITY_STATUS = WORKSPACE / "email_search_integrity_status.json"
APP_IMPROVEMENT_READINESS_STATUS = WORKSPACE / "app_improvement_readiness_status.json"
LEARNING_REPAIR_STATUS = WORKSPACE / "repair_learning_engine_status.json"
PAPERLESS_RAG_WATCHDOG_STATUS = WORKSPACE / "paperless_rag_watchdog_status.json"
PAPERLESS_INGEST_STATUS = WORKSPACE / "ingest_watchdog_status.json"
PAPERLESS_REVIEW_ARTIFACT_STATUS = WORKSPACE / "paperless_pdf_review_artifacts_status.json"
PAPERLESS_INGEST_AUDIT_STATUS = WORKSPACE / "paperless_ingest_audit_status.json"
PAPERLESS_INGEST_CONFIG_PATH = WORKSPACE / "paperless_ingest_config.json"
PAPERLESS_TOKEN_REFRESH_STATUS = WORKSPACE / "paperless_token_refresh_status.json"
DOCKER_DESKTOP_UI_WATCHDOG_STATUS = WORKSPACE / "docker_desktop_ui_watchdog_status.json"
CLAUDIAN_WATCHDOG_STATUS = WORKSPACE / "claudian_watchdog_status.json"
MINIPC_OPTIMIZER_WATCHDOG_STATUS = WORKSPACE / "minipc_optimizer_watchdog_status.json"
EMAIL_BLACKLIST_HUB_STATUS = WORKSPACE / "email_blacklist_hub_status.json"
EMAIL_FILTER_PATH = WORKSPACE / "email_rag_sender_filters.json"
EMAIL_SEARCH_API_LOG = WORKSPACE / "email_search_api.log"

START_EMAIL_WATCHDOG = ROOT / "scripts" / "start_email_continuous_watchdog.ps1"
START_DOCKER_UI_WATCHDOG = ROOT / "scripts" / "start_docker_desktop_ui_watchdog.ps1"
START_CLAUDIAN_WATCHDOG = ROOT / "scripts" / "start_claudian_watchdog.ps1"
START_MINIPC_OPTIMIZER_WATCHDOG = ROOT / "scripts" / "start_minipc_optimizer_watchdog.ps1"
START_EMAIL_BLACKLIST_HUB = ROOT / "scripts" / "start_email_blacklist_hub_api.ps1"
START_EMAIL_SEARCH_API = ROOT / "scripts" / "start_email_search_api.ps1"
LEARNING_HEALTH_URLS = [
    "http://localhost:8110/health",
    "http://127.0.0.1:8110/health",
    "http://host.docker.internal:8110/health",
]
EMAIL_BLACKLIST_HUB_URL = "http://127.0.0.1:8791/api/email-blacklist/config"
EMAIL_BLACKLIST_CANDIDATES_URL = "http://127.0.0.1:8791/api/email-blacklist/candidates"
EMAIL_SEARCH_STATS_URL = "http://127.0.0.1:8792/api/stats"
DOCKER_SERVICE_KEYS = {
    "clawdbot-gateway",
    "portal_server",
    "ollama",
    "qdrant",
    "litellm",
    "postgres",
    "redis",
    "n8n",
    "quality_dashboard",
    "mfg-sim",
    "mailpit",
    "searxng",
    "prometheus",
    "open_webui",
}
HOST_API_PROBES = [
    {"key": "portal", "title": "Portal", "url": "http://127.0.0.1:8088/portal.html", "kind": "html"},
    {"key": "gateway_control", "title": "Gateway Control UI", "url": "http://127.0.0.1:8099", "kind": "html"},
    {"key": "email_search_api", "title": "Email Search API", "url": EMAIL_SEARCH_STATS_URL, "kind": "json"},
    {"key": "email_blacklist_hub", "title": "Email Blacklist Hub API", "url": EMAIL_BLACKLIST_HUB_URL, "kind": "json"},
    {"key": "learning_engine", "title": "Learning Engine", "url": "http://127.0.0.1:8110/health", "kind": "json"},
]


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: dict[str, Any]) -> None:
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


def age_minutes(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((now_jst().astimezone(dt.tzinfo) - dt).total_seconds() / 60.0, 1)


def run_shell(command: list[str], timeout_seconds: int = 300) -> dict[str, Any]:
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


def start_detached(command: list[str]) -> dict[str, Any]:
    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
        return {
            "command": " ".join(command),
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timedOut": False,
            "startedPid": proc.pid,
        }
    except Exception as exc:
        return {
            "command": " ".join(command),
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "timedOut": False,
        }


def process_exists(token: str) -> bool:
    ps_script = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "Select-Object -First 1 ProcessId | ConvertTo-Json -Compress"
    )
    result = run_shell(["powershell", "-NoProfile", "-Command", ps_script], 30)
    return bool(result.get("stdout") and "ProcessId" in result["stdout"])


def process_commandline(token: str) -> str | None:
    ps_script = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{token}*' }} | "
        "Select-Object -First 1 -ExpandProperty CommandLine"
    )
    result = run_shell(["powershell", "-NoProfile", "-Command", ps_script], 30)
    commandline = str(result.get("stdout") or "").strip()
    return commandline or None


def learning_health() -> dict[str, Any]:
    attempts = []
    for url in LEARNING_HEALTH_URLS:
        try:
            resp = requests.get(url, timeout=10)
            attempts.append({"url": url, "status": resp.status_code})
            if resp.ok:
                payload = resp.json()
                return {
                    "ok": True,
                    "url": url,
                    "status": resp.status_code,
                    "qdrant": payload.get("qdrant"),
                    "collections": len(payload.get("collections") or []),
                    "attempts": attempts,
                }
        except Exception as exc:
            attempts.append({"url": url, "error": str(exc)})
    return {"ok": False, "attempts": attempts}


def probe_json_api(url: str, timeout_seconds: int = 8) -> dict[str, Any]:
    try:
        resp = requests.get(url, timeout=timeout_seconds)
        payload = None
        if resp.headers.get("content-type", "").lower().startswith("application/json"):
            payload = resp.json()
        auth_failure = resp.status_code in {401, 403}
        return {
            "ok": resp.ok and not auth_failure,
            "url": url,
            "status": resp.status_code,
            "payload": payload,
            "authFailure": auth_failure,
            "error": f"HTTP {resp.status_code}" if not (resp.ok and not auth_failure) else None,
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc), "authFailure": False}


def probe_http(url: str, timeout_seconds: int = 8) -> dict[str, Any]:
    try:
        resp = requests.get(url, timeout=timeout_seconds)
        auth_failure = resp.status_code in {401, 403}
        return {
            "ok": resp.ok and not auth_failure,
            "url": url,
            "status": resp.status_code,
            "contentType": resp.headers.get("content-type", ""),
            "authFailure": auth_failure,
            "error": f"HTTP {resp.status_code}" if not (resp.ok and not auth_failure) else None,
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc), "authFailure": False}


def load_paperless_ingest_config() -> dict[str, Any]:
    return read_json(PAPERLESS_INGEST_CONFIG_PATH, {})


def candidate_host_urls(base_url: str) -> list[str]:
    value = str(base_url or "").strip()
    urls: list[str] = []
    if value:
        urls.append(value.rstrip("/"))
        if "://host.docker.internal:" in value:
            urls.append(value.replace("://host.docker.internal:", "://127.0.0.1:").rstrip("/"))
            urls.append(value.replace("://host.docker.internal:", "://localhost:").rstrip("/"))
        if "://paperless:" in value:
            urls.append(value.replace("://paperless:", "://127.0.0.1:").rstrip("/"))
            urls.append(value.replace("://paperless:", "://localhost:").rstrip("/"))
    for fallback in ("http://127.0.0.1:8000", "http://localhost:8000"):
        if fallback not in urls:
            urls.append(fallback)
    return urls


def probe_paperless_auth(timeout_seconds: int = 8) -> dict[str, Any]:
    config = load_paperless_ingest_config()
    token = str(config.get("paperlessToken") or "").strip()
    base_url = str(config.get("paperlessUrl") or "").strip()
    if not token:
        return {
            "key": "paperless_ingest_auth",
            "title": "Paperless Ingest API",
            "url": base_url or "http://127.0.0.1:8000",
            "ok": False,
            "status": None,
            "error": "missing token",
            "authFailure": False,
        }
    headers = {"Authorization": f"Token {token}"}
    last_error = "missing candidate URL"
    for candidate in candidate_host_urls(base_url):
        try:
            resp = requests.get(f"{candidate}/api/documents/?page_size=1", headers=headers, timeout=timeout_seconds)
            auth_failure = resp.status_code in {401, 403}
            return {
                "key": "paperless_ingest_auth",
                "title": "Paperless Ingest API",
                "url": candidate,
                "ok": resp.ok and not auth_failure,
                "status": resp.status_code,
                "error": f"HTTP {resp.status_code}" if not (resp.ok and not auth_failure) else None,
                "authFailure": auth_failure,
            }
        except Exception as exc:
            last_error = str(exc)
    return {
        "key": "paperless_ingest_auth",
        "title": "Paperless Ingest API",
        "url": base_url or "http://127.0.0.1:8000",
        "ok": False,
        "status": None,
        "error": last_error,
        "authFailure": False,
    }


def collect_host_api_inventory() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for probe in HOST_API_PROBES:
        result = probe_json_api(probe["url"]) if probe["kind"] == "json" else probe_http(probe["url"])
        items.append(
            {
                "key": probe["key"],
                "title": probe["title"],
                "url": probe["url"],
                "ok": bool(result.get("ok")),
                "status": result.get("status"),
                "error": result.get("error"),
                "authFailure": bool(result.get("authFailure")),
            }
        )
    items.append(probe_paperless_auth())
    return items


def collect_service_inventory() -> list[dict[str, Any]]:
    result = run_shell(["docker", "ps", "-a", "--format", "{{json .}}"], 60)
    if result.get("returncode") != 0:
        return []
    items: list[dict[str, Any]] = []
    for line in str(result.get("stdout") or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        name = str(payload.get("Names") or "")
        service = name.removeprefix("clawstack-unified-")
        if service.endswith("-1"):
            service = service[:-2]
        if service not in DOCKER_SERVICE_KEYS:
            continue
        status_text = str(payload.get("Status") or "")
        items.append(
            {
                "key": service,
                "title": service,
                "container": name,
                "status": status_text,
                "running": status_text.lower().startswith("up "),
            }
        )
    items.sort(key=lambda item: item["title"])
    return items


def gateway_ingest_watchdog_count() -> int | None:
    result = run_shell(
        [
            "docker",
            "exec",
            "clawstack-unified-clawdbot-gateway-1",
            "sh",
            "-lc",
            "pgrep -fc '^python3 /home/node/clawd/ingest_watchdog.py$' || true",
        ],
        30,
    )
    if result.get("returncode") != 0:
        return None
    try:
        return int(str(result.get("stdout") or "").strip() or "0")
    except Exception:
        return None


def extract_gmail_summary(email_daemon: dict[str, Any]) -> dict[str, Any]:
    summary = ((email_daemon.get("lastSummary") or {}).get("index") or {}).get("gmail")
    if isinstance(summary, dict) and summary:
        return summary
    stdout = str((email_daemon.get("lastIndexResult") or {}).get("stdout") or "").strip()
    if stdout:
        try:
            payload = json.loads(stdout)
            gmail = payload.get("gmail")
            if isinstance(gmail, dict):
                return gmail
        except Exception:
            pass
    return {}


def status_health(payload: dict[str, Any], keys: list[str], max_age_minutes: int) -> tuple[bool, float | None, str]:
    stamp = None
    for key in keys:
        stamp = payload.get(key)
        if stamp:
            break
    dt = parse_dt(stamp)
    age = age_minutes(dt)
    if dt is None:
        return False, None, "missing"
    if age is not None and age > max_age_minutes:
        return False, age, "stale"
    return True, age, "healthy"


def summarize() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    email_watchdog = read_json(EMAIL_WATCHDOG_STATUS, {})
    email_daemon = read_json(EMAIL_DAEMON_STATUS, {})
    idle = read_json(IDLE_STATUS, {})
    auto_repair = read_json(AUTO_REPAIR_STATUS, {})
    risk_notification = read_json(RISK_NOTIFICATION_STATUS, {})
    email_quality = read_json(EMAIL_QUALITY_STATUS, {})
    email_integrity = read_json(EMAIL_INTEGRITY_STATUS, {})
    app_readiness = read_json(APP_IMPROVEMENT_READINESS_STATUS, {})
    learning_repair = read_json(LEARNING_REPAIR_STATUS, {})
    paperless_watchdog = read_json(PAPERLESS_RAG_WATCHDOG_STATUS, {})
    paperless_ingest = read_json(PAPERLESS_INGEST_STATUS, {})
    paperless_review_artifacts = read_json(PAPERLESS_REVIEW_ARTIFACT_STATUS, {})
    paperless_ingest_audit = read_json(PAPERLESS_INGEST_AUDIT_STATUS, {})
    paperless_token_refresh = read_json(PAPERLESS_TOKEN_REFRESH_STATUS, {})
    docker_ui_watchdog = read_json(DOCKER_DESKTOP_UI_WATCHDOG_STATUS, {})
    claudian_watchdog = read_json(CLAUDIAN_WATCHDOG_STATUS, {})
    minipc_optimizer_watchdog = read_json(MINIPC_OPTIMIZER_WATCHDOG_STATUS, {})
    email_blacklist_hub = read_json(EMAIL_BLACKLIST_HUB_STATUS, {})
    email_policy = read_json(EMAIL_POLICY_PATH, {})
    outbound_guard = read_json(OUTBOUND_GUARD_STATUS_PATH, {})
    email_filters = read_json(EMAIL_FILTER_PATH, {})
    learning = learning_health()
    blacklist_config = probe_json_api(EMAIL_BLACKLIST_HUB_URL)
    blacklist_candidates = probe_json_api(EMAIL_BLACKLIST_CANDIDATES_URL)
    email_search_stats = probe_json_api(EMAIL_SEARCH_STATS_URL)
    host_api_inventory = collect_host_api_inventory()
    service_inventory = collect_service_inventory()
    gateway_ingest_count = gateway_ingest_watchdog_count()
    paperless_auth_probe = next((item for item in host_api_inventory if item.get("key") == "paperless_ingest_auth"), {})

    strengths: list[dict[str, Any]] = []
    weaknesses: list[dict[str, Any]] = []

    watchdog_ok, watchdog_age, watchdog_state = status_health(email_watchdog, ["updatedAt"], 20)
    if watchdog_ok and process_exists("email_continuous_watchdog.py"):
        strengths.append({"key": "email_watchdog", "title": "Email watchdog is running", "detail": f"updated {watchdog_age} minutes ago"})
    else:
        weaknesses.append({"key": "email_watchdog", "severity": "high", "title": "Email watchdog is missing or stale", "detail": f"state={watchdog_state} ageMinutes={watchdog_age}"})

    daemon_ok, daemon_age, daemon_state = status_health(email_daemon, ["updatedAt", "lastSuccessAt"], 20)
    daemon_stage = str(email_daemon.get("stage") or "")
    daemon_last_success = parse_dt(str(email_daemon.get("lastSuccessAt") or ""))
    daemon_last_success_age = age_minutes(daemon_last_success)
    daemon_process_alive = process_exists("continuous_email_ingest_daemon.py")
    healthy_daemon_stages = {"idle", "indexing", "sync_learning", "dashboard_refresh", "full_backfill"}
    transient_error = (
        daemon_stage == "error"
        and daemon_process_alive
        and daemon_age is not None
        and daemon_age <= 5
        and daemon_last_success_age is not None
        and daemon_last_success_age <= 720
    )
    if daemon_ok and daemon_stage in healthy_daemon_stages:
        strengths.append({"key": "email_daemon", "title": "Continuous email ingest is active", "detail": f"stage={daemon_stage} age={daemon_age} minutes"})
    elif transient_error:
        strengths.append({"key": "email_daemon", "title": "Continuous email ingest heartbeat is active", "detail": f"stage=error but process alive and heartbeat age={daemon_age} minutes"})
        weaknesses.append({"key": "email_daemon_transient", "severity": "medium", "title": "Continuous email ingest reported a transient error", "detail": f"stage=error ageMinutes={daemon_age} lastSuccessAgeMinutes={daemon_last_success_age}"})
    else:
        weaknesses.append({"key": "email_daemon", "severity": "high", "title": "Continuous email ingest is unhealthy", "detail": f"stage={daemon_stage or 'unknown'} state={daemon_state} ageMinutes={daemon_age}"})

    auto_ok, auto_age, auto_state = status_health(auto_repair, ["finishedAt", "startedAt"], 120)
    if auto_ok and auto_repair.get("step") == "completed":
        strengths.append({"key": "auto_repair", "title": "Auto repair patrol is recent", "detail": f"updated {auto_age} minutes ago"})
    else:
        weaknesses.append({"key": "auto_repair", "severity": "medium", "title": "Auto repair patrol is stale", "detail": f"state={auto_state} ageMinutes={auto_age}"})

    idle_ok, idle_age, idle_state = status_health(idle, ["finishedAt", "startedAt"], 120)
    if idle_ok and idle.get("step") == "completed":
        strengths.append({"key": "idle_maintenance", "title": "Idle maintenance is recent", "detail": f"updated {idle_age} minutes ago"})
    else:
        weaknesses.append({"key": "idle_maintenance", "severity": "medium", "title": "Idle maintenance is stale", "detail": f"state={idle_state} ageMinutes={idle_age}"})

    risk_ok, risk_age, risk_state = status_health(risk_notification, ["finishedAt", "startedAt"], 180)
    if risk_ok and risk_notification.get("step") == "completed":
        strengths.append({"key": "risk_notification", "title": "Risk notification patrol is recent", "detail": f"updated {risk_age} minutes ago"})
    else:
        weaknesses.append({"key": "risk_notification", "severity": "medium", "title": "Risk notification patrol is stale", "detail": f"state={risk_state} ageMinutes={risk_age}"})

    learning_repair_result = str(learning_repair.get("result") or "")
    learning_repair_skipped = learning_repair_result == "skipped_in_headless_native_mode"
    if learning.get("ok"):
        strengths.append({"key": "learning_engine", "title": "Learning engine health endpoint is reachable", "detail": f"url={learning.get('url')} collections={learning.get('collections')}"})
    elif learning_repair_skipped:
        strengths.append({"key": "learning_engine_headless_mode", "title": "Learning engine repair is intentionally disabled in headless native mode", "detail": "Current docker runtime is wsl_native; health probe remains offline by design"})
    else:
        repair_age_ok, repair_age, _ = status_health(learning_repair, ["finishedAt", "startedAt"], 180)
        repair_detail = "all configured health URLs failed"
        if learning_repair:
            repair_detail = f"all configured health URLs failed; lastRepairResult={learning_repair.get('result')} repairAgeMinutes={repair_age if repair_age_ok else repair_age}"
        weaknesses.append({"key": "learning_engine", "severity": "high", "title": "Learning engine health endpoint is offline", "detail": repair_detail})

    paperless_watchdog_ok, paperless_watchdog_age, paperless_watchdog_state = status_health(paperless_watchdog, ["updatedAt"], 20)
    if paperless_watchdog_ok and str(paperless_watchdog.get("stage") or "") in {"healthy", "running", "starting", "warming_up"}:
        strengths.append({"key": "paperless_rag_watchdog", "title": "Paperless RAG watchdog is active", "detail": f"updated {paperless_watchdog_age} minutes ago"})
    else:
        weaknesses.append({"key": "paperless_rag_watchdog", "severity": "high", "title": "Paperless RAG watchdog is stale", "detail": f"state={paperless_watchdog_state} ageMinutes={paperless_watchdog_age}"})
    if gateway_ingest_count is not None and gateway_ingest_count <= 1:
        strengths.append({"key": "gateway_ingest_watchdog_count", "title": "Gateway ingest watchdog process count is healthy", "detail": f"processes={gateway_ingest_count}"})
    elif gateway_ingest_count is not None:
        weaknesses.append({"key": "gateway_ingest_watchdog_count", "severity": "high", "title": "Gateway has duplicate ingest watchdog processes", "detail": f"processes={gateway_ingest_count}"})

    paperless_ingest_ok, paperless_ingest_age, paperless_ingest_state = status_health(paperless_ingest, ["updatedAt"], 20)
    paperless_stage = str(paperless_ingest.get("stage") or "")
    if paperless_ingest_ok and paperless_stage in {"starting", "polling", "processing", "processing_batch", "idle"}:
        strengths.append({"key": "paperless_ingest", "title": "Paperless ingest heartbeat is fresh", "detail": f"stage={paperless_stage} age={paperless_ingest_age} minutes"})
    else:
        weaknesses.append({"key": "paperless_ingest", "severity": "high", "title": "Paperless ingest heartbeat is unhealthy", "detail": f"stage={paperless_stage or 'unknown'} state={paperless_ingest_state} ageMinutes={paperless_ingest_age}"})

    paperless_review_ok, paperless_review_age, paperless_review_state = status_health(paperless_review_artifacts, ["updatedAt"], 720)
    if paperless_review_ok and bool(paperless_review_artifacts.get("ok")):
        strengths.append({"key": "paperless_review_artifacts", "title": "Paperless review artifacts are recent", "detail": f"age={paperless_review_age} minutes reason={paperless_review_artifacts.get('reason')}"})
    else:
        weaknesses.append({"key": "paperless_review_artifacts", "severity": "medium", "title": "Paperless review artifacts are stale or failed", "detail": f"state={paperless_review_state} ok={paperless_review_artifacts.get('ok')}"})

    paperless_audit_ok, paperless_audit_age, paperless_audit_state = status_health(paperless_ingest_audit, ["updatedAt"], 720)
    if str(paperless_ingest_audit.get("status") or "") == "healthy" and not (paperless_ingest_audit.get("recentMissing") or []):
        strengths.append({"key": "paperless_ingest_audit", "title": "Paperless ingest audit confirms recent documents are indexed", "detail": f"age={paperless_audit_age} minutes"})
    else:
        missing = len(paperless_ingest_audit.get("recentMissing") or [])
        weaknesses.append({"key": "paperless_ingest_audit", "severity": "high", "title": "Paperless ingest audit found lag or is stale", "detail": f"state={paperless_audit_state} status={paperless_ingest_audit.get('status')} recentMissing={missing}"})

    if paperless_auth_probe:
        if paperless_auth_probe.get("ok"):
            strengths.append(
                {
                    "key": "paperless_ingest_auth",
                    "title": "Paperless ingest API authentication is valid",
                    "detail": f"url={paperless_auth_probe.get('url')} status={paperless_auth_probe.get('status')}",
                }
            )
        else:
            severity = "high" if paperless_auth_probe.get("authFailure") else "medium"
            title = "Paperless ingest API authentication failed" if paperless_auth_probe.get("authFailure") else "Paperless ingest API is unavailable"
            weaknesses.append(
                {
                    "key": "paperless_ingest_auth",
                    "severity": severity,
                    "title": title,
                    "detail": f"url={paperless_auth_probe.get('url')} detail={paperless_auth_probe.get('error')}",
                }
            )

    for api_probe in host_api_inventory:
        if api_probe.get("authFailure") and api_probe.get("key") != "paperless_ingest_auth":
            weaknesses.append(
                {
                    "key": f"host_api_auth_{api_probe.get('key')}",
                    "severity": "high",
                    "title": f"{api_probe.get('title')} returned auth failure",
                    "detail": f"url={api_probe.get('url')} status={api_probe.get('status')}",
                }
            )

    docker_ui_ok, docker_ui_age, docker_ui_state = status_health(docker_ui_watchdog, ["updatedAt"], 30)
    docker_ui_stage = str(docker_ui_watchdog.get("stage") or "")
    if docker_ui_ok and docker_ui_stage in {"healthy", "starting", "repairing", "suppressing"} and process_exists("docker_desktop_ui_watchdog.py"):
        strengths.append({"key": "docker_desktop_ui_watchdog", "title": "Docker Desktop UI watchdog is active", "detail": f"stage={docker_ui_stage} age={docker_ui_age} minutes"})
    else:
        weaknesses.append({"key": "docker_desktop_ui_watchdog", "severity": "medium", "title": "Docker Desktop UI watchdog is stale or missing", "detail": f"state={docker_ui_state} stage={docker_ui_stage or 'unknown'} ageMinutes={docker_ui_age}"})

    claudian_ok, claudian_age, claudian_state = status_health(claudian_watchdog, ["updatedAt"], 30)
    claudian_stage = str(claudian_watchdog.get("stage") or "")
    if claudian_ok and claudian_stage in {"healthy", "warning"} and process_exists("claudian_watchdog.py"):
        strengths.append({"key": "claudian_watchdog", "title": "Claudian watchdog is active", "detail": f"stage={claudian_stage} age={claudian_age} minutes"})
    else:
        weaknesses.append({"key": "claudian_watchdog", "severity": "medium", "title": "Claudian watchdog is stale or missing", "detail": f"state={claudian_state} stage={claudian_stage or 'unknown'} ageMinutes={claudian_age}"})

    minipc_ok, minipc_age, minipc_state = status_health(minipc_optimizer_watchdog, ["updatedAt"], 30)
    minipc_stage = str(minipc_optimizer_watchdog.get("stage") or "")
    if minipc_ok and minipc_stage in {"healthy", "cooldown", "completed", "evaluating"} and process_exists("minipc_optimizer_watchdog.py"):
        strengths.append({"key": "minipc_optimizer_watchdog", "title": "Mini PC optimizer watchdog is active", "detail": f"stage={minipc_stage} age={minipc_age} minutes"})
    else:
        weaknesses.append({"key": "minipc_optimizer_watchdog", "severity": "medium", "title": "Mini PC optimizer watchdog is stale or missing", "detail": f"state={minipc_state} stage={minipc_stage or 'unknown'} ageMinutes={minipc_age}"})

    blacklist_ok, blacklist_age, blacklist_state = status_health(email_blacklist_hub, ["updatedAt"], 180)
    blacklist_process_alive = process_exists("email_blacklist_hub_api.py")
    blacklist_count = len(email_filters.get("blacklist_patterns") or [])
    if blacklist_process_alive and blacklist_config.get("ok") and blacklist_candidates.get("ok"):
        candidate_count = len((blacklist_candidates.get("payload") or {}).get("candidates") or [])
        strengths.append(
            {
                "key": "email_blacklist_hub",
                "title": "Email blacklist hub API is reachable",
                "detail": f"blacklist={blacklist_count} candidates={candidate_count}",
            }
        )
    else:
        detail = (
            f"processAlive={blacklist_process_alive} state={blacklist_state} ageMinutes={blacklist_age} "
            f"configOk={blacklist_config.get('ok')} candidatesOk={blacklist_candidates.get('ok')}"
        )
        weaknesses.append(
            {
                "key": "email_blacklist_hub",
                "severity": "high",
                "title": "Email blacklist hub API is offline or stale",
                "detail": detail,
            }
        )

    email_search_process_alive = process_exists("email_search_api.py")
    if email_search_process_alive and email_search_stats.get("ok"):
        payload = email_search_stats.get("payload") or {}
        strengths.append(
            {
                "key": "email_search_api",
                "title": "Email search API is reachable",
                "detail": f"emails={payload.get('total_emails', '?')} tasks={payload.get('total_tasks', '?')}",
            }
        )
    else:
        weaknesses.append(
            {
                "key": "email_search_api",
                "severity": "high",
                "title": "Email search API is offline",
                "detail": f"processAlive={email_search_process_alive} apiOk={email_search_stats.get('ok')}",
            }
        )

    quality_ok, quality_age, quality_state = status_health(email_quality, ["finishedAt", "startedAt"], 720)
    metrics = email_quality.get("metrics") or {}
    if quality_ok and metrics:
        strengths.append(
            {
                "key": "email_quality",
                "title": "Email extraction quality snapshot is recent",
                "detail": f"deadline_detection_rate={metrics.get('deadline_detection_rate', 0)}% reply_detail_detection_rate={metrics.get('reply_detail_detection_rate', 0)}%",
            }
        )
        if float(metrics.get("deadline_detection_rate", 0.0)) < 80.0:
            weaknesses.append({"key": "email_quality_deadline", "severity": "medium", "title": "Deadline extraction rate is below target", "detail": f"rate={metrics.get('deadline_detection_rate')}%"})
        if float(metrics.get("reply_detail_detection_rate", 0.0)) < 80.0:
            weaknesses.append({"key": "email_quality_reply", "severity": "medium", "title": "Reply detail extraction rate is below target", "detail": f"rate={metrics.get('reply_detail_detection_rate')}%"})
    else:
        weaknesses.append({"key": "email_quality", "severity": "medium", "title": "Email extraction quality snapshot is missing or stale", "detail": f"state={quality_state} ageMinutes={quality_age}"})

    email_policy_ok = bool((email_policy.get("email") or {}).get("draft_only", False) and (email_policy.get("email") or {}).get("auto_send", True) is False)
    if email_policy_ok:
        strengths.append({"key": "email_policy", "title": "Email safety policy is present", "detail": "draft_only=true auto_send=false"})
    else:
        weaknesses.append({"key": "email_policy", "severity": "high", "title": "Email safety policy is missing or unsafe", "detail": "expected draft_only=true and auto_send=false"})

    outbound_guard_ok = bool(
        outbound_guard.get("policyActive")
        and str(outbound_guard.get("allowedGmailRecipient") or "").strip().lower() == "y.suzuki.hk@gmail.com"
        and str(outbound_guard.get("allowedTelegramChatId") or "").strip() == "8173025084"
    )
    if outbound_guard_ok:
        strengths.append(
            {
                "key": "outbound_delivery_guard",
                "title": "Outbound delivery allowlist guard is enforced",
                "detail": (
                    f"gmail={outbound_guard.get('allowedGmailRecipient')} "
                    f"telegram={outbound_guard.get('allowedTelegramChatId')} "
                    f"blocked={outbound_guard.get('blockedCount', 0)}"
                ),
            }
        )
    else:
        weaknesses.append(
            {
                "key": "outbound_delivery_guard",
                "severity": "high",
                "title": "Outbound delivery guard is missing or drifted",
                "detail": "Expected Gmail=y.suzuki.hk@gmail.com and Telegram chat_id=8173025084 in the enforced allowlist",
            }
        )

    integrity_ok, integrity_age, integrity_state = status_health(email_integrity, ["finishedAt", "startedAt"], 720)
    if integrity_ok and bool(email_integrity.get("ok")):
        strengths.append({"key": "email_integrity", "title": "Email SQLite integrity check is recent", "detail": f"age={integrity_age} minutes"})
    else:
        weaknesses.append({"key": "email_integrity", "severity": "high", "title": "Email SQLite integrity check failed or is stale", "detail": f"state={integrity_state} ok={email_integrity.get('ok')}"})

    daemon_commandline = process_commandline("continuous_email_ingest_daemon.py") or ""
    if "--skip-full-backfill" in daemon_commandline:
        weaknesses.append(
            {
                "key": "email_backfill_spec",
                "severity": "high",
                "title": "Continuous email ingest drifted away from historical backfill",
                "detail": "continuous_email_ingest_daemon.py is running with --skip-full-backfill",
            }
        )
    else:
        backfill = ((email_daemon.get("lastSummary") or {}).get("backfill") or {})
        if str(backfill.get("startDate") or "") == "2026-01-01":
            strengths.append(
                {
                    "key": "email_backfill_spec",
                    "title": "Historical Gmail backfill still targets January 2026 onward",
                    "detail": f"last range {backfill.get('startDate')}..{backfill.get('endDateInclusive')}",
                }
            )

    gmail_summary = extract_gmail_summary(email_daemon)
    if blacklist_count > 0:
        if "skipped_by_filter" in gmail_summary or "skippedByFilter" in gmail_summary:
            skipped_by_filter = gmail_summary.get("skipped_by_filter", gmail_summary.get("skippedByFilter", 0))
            strengths.append(
                {
                    "key": "email_filter_telemetry",
                    "title": "Gmail filter telemetry is visible in ingest summaries",
                    "detail": f"skipped_by_filter={skipped_by_filter}",
                }
            )
        else:
            weaknesses.append(
                {
                    "key": "email_filter_telemetry",
                    "severity": "medium",
                    "title": "Gmail filter telemetry is missing from ingest summaries",
                    "detail": "Expected skipped_by_filter in recent Gmail summary so blacklist effectiveness stays observable",
                }
            )

    readiness = str(app_readiness.get("readiness") or "")
    if readiness == "ready":
        strengths.append({"key": "app_readiness", "title": "Improvement readiness checks are all passing", "detail": f"{app_readiness.get('passedChecks', 0)}/{app_readiness.get('totalChecks', 0)} checks passed"})
    elif app_readiness:
        weaknesses.append({"key": "app_readiness", "severity": "medium", "title": "Improvement readiness is partial", "detail": f"{app_readiness.get('passedChecks', 0)}/{app_readiness.get('totalChecks', 0)} checks passed"})

    context = {
        "emailWatchdog": email_watchdog,
        "emailDaemon": email_daemon,
        "idleMaintenance": idle,
        "autoRepair": auto_repair,
        "riskNotification": risk_notification,
        "emailQuality": email_quality,
        "emailIntegrity": email_integrity,
        "appReadiness": app_readiness,
        "learningRepair": learning_repair,
        "paperlessWatchdog": paperless_watchdog,
        "paperlessIngest": paperless_ingest,
        "paperlessReviewArtifacts": paperless_review_artifacts,
        "paperlessIngestAudit": paperless_ingest_audit,
        "dockerDesktopUiWatchdog": docker_ui_watchdog,
        "claudianWatchdog": claudian_watchdog,
        "minipcOptimizerWatchdog": minipc_optimizer_watchdog,
        "emailBlacklistHub": email_blacklist_hub,
        "paperlessTokenRefresh": paperless_token_refresh,
        "emailFilters": email_filters,
        "blacklistConfig": blacklist_config,
        "blacklistCandidates": blacklist_candidates,
        "emailSearchStats": email_search_stats,
        "emailPolicy": email_policy,
        "outboundDeliveryGuard": outbound_guard,
        "learningHealth": learning,
        "hostApiInventory": host_api_inventory,
        "serviceInventory": service_inventory,
        "gatewayIngestWatchdogCount": gateway_ingest_count,
        "paperlessAuthProbe": paperless_auth_probe,
    }
    return strengths, weaknesses, context


def planned_actions(weaknesses: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    weakness_keys = {item["key"] for item in weaknesses}
    if "email_watchdog" in weakness_keys:
        actions.append({"key": "start_email_watchdog", "reason": "Email watchdog is missing or stale"})
    if "docker_desktop_ui_watchdog" in weakness_keys:
        actions.append({"key": "start_docker_desktop_ui_watchdog", "reason": "Docker Desktop UI watchdog is missing or stale"})
    if "claudian_watchdog" in weakness_keys:
        actions.append({"key": "start_claudian_watchdog", "reason": "Claudian watchdog is missing or stale"})
    if "minipc_optimizer_watchdog" in weakness_keys:
        actions.append({"key": "start_minipc_optimizer_watchdog", "reason": "Mini PC optimizer watchdog is missing or stale"})
    if "email_blacklist_hub" in weakness_keys:
        actions.append({"key": "start_email_blacklist_hub", "reason": "Email blacklist hub API is offline or stale"})
    if "email_search_api" in weakness_keys:
        actions.append({"key": "start_email_search_api", "reason": "Email search API is offline"})
    if "auto_repair" in weakness_keys or "email_daemon" in weakness_keys:
        actions.append({"key": "run_auto_repair", "reason": "Auto repair should re-evaluate email-related health"})
    if "idle_maintenance" in weakness_keys:
        actions.append({"key": "run_idle_maintenance", "reason": "Refresh maintenance cadence and status"})
    if "risk_notification" in weakness_keys or "learning_engine" in weakness_keys:
        actions.append({"key": "run_risk_notification", "reason": "Push current risks through notification patrol"})
    if "learning_engine" in weakness_keys:
        actions.append({"key": "run_learning_engine_repair", "reason": "Recover learning_engine and Docker path if 8110 is offline"})
    if "email_quality" in weakness_keys or "email_quality_deadline" in weakness_keys or "email_quality_reply" in weakness_keys:
        actions.append({"key": "run_email_quality_eval", "reason": "Refresh Gmail extraction quality metrics"})
    if "email_integrity" in weakness_keys:
        actions.append({"key": "run_email_integrity_check", "reason": "Refresh SQLite integrity status and catch corruption early"})
    if "app_readiness" in weakness_keys:
        actions.append({"key": "run_app_readiness_eval", "reason": "Refresh promotion-rule and success-criteria checks"})
    if "gateway_ingest_watchdog_count" in weakness_keys:
        actions.append({"key": "run_paperless_rag_watchdog", "reason": "Paperless watchdog should collapse duplicate ingest processes"})
    if "paperless_ingest_auth" in weakness_keys:
        actions.append({"key": "refresh_paperless_ingest_token", "reason": "Paperless ingest auth should mint a fresh token when 401/403 occurs"})
        actions.append({"key": "run_paperless_rag_watchdog", "reason": "Paperless watchdog should restart ingest after token refresh"})
    return actions


def execute_action(action_key: str) -> dict[str, Any]:
    if action_key == "start_email_watchdog":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_EMAIL_WATCHDOG),
            ]
        )
    if action_key == "start_docker_desktop_ui_watchdog":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_DOCKER_UI_WATCHDOG),
            ]
        )
    if action_key == "start_claudian_watchdog":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_CLAUDIAN_WATCHDOG),
            ]
        )
    if action_key == "start_minipc_optimizer_watchdog":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_MINIPC_OPTIMIZER_WATCHDOG),
            ]
        )
    if action_key == "start_email_blacklist_hub":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_EMAIL_BLACKLIST_HUB),
            ]
        )
    if action_key == "start_email_search_api":
        return start_detached(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(START_EMAIL_SEARCH_API),
            ]
        )
    if action_key == "run_auto_repair":
        return run_shell(["python3", str(WORKSPACE / "auto_repair_allowed.py")], 600)
    if action_key == "run_idle_maintenance":
        return run_shell(["python3", str(WORKSPACE / "idle_ingest_maintenance.py")], 7200)
    if action_key == "run_risk_notification":
        return run_shell(["python3", str(WORKSPACE / "risk_notification.py")], 600)
    if action_key == "run_learning_engine_repair":
        return run_shell(["python3", str(WORKSPACE / "repair_learning_engine.py")], 1200)
    if action_key == "run_email_quality_eval":
        return run_shell(["python3", str(WORKSPACE / "evaluate_email_request_quality.py")], 600)
    if action_key == "run_email_integrity_check":
        return run_shell(["python3", str(WORKSPACE / "check_email_search_integrity.py")], 600)
    if action_key == "run_app_readiness_eval":
        return run_shell(["python3", str(WORKSPACE / "evaluate_app_improvement_readiness.py")], 600)
    if action_key == "run_paperless_rag_watchdog":
        return run_shell(["python3", str(WORKSPACE / "paperless_rag_watchdog.py"), "--once"], 180)
    if action_key == "refresh_paperless_ingest_token":
        return run_shell(["python3", str(WORKSPACE / "refresh_paperless_ingest_token.py")], 180)
    return {"command": action_key, "returncode": 1, "stdout": "", "stderr": "unknown action", "timedOut": False}


def write_summary(strengths: list[dict[str, Any]], weaknesses: list[dict[str, Any]], actions: list[dict[str, Any]]) -> None:
    lines = [
        f"# Continuous System Improvement Summary",
        "",
        f"Updated: {now_jst_text()}",
        "",
        "## Strengths",
    ]
    if strengths:
        for item in strengths:
            lines.append(f"- {item['title']}: {item['detail']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Weaknesses"])
    if weaknesses:
        for item in weaknesses:
            lines.append(f"- [{item['severity'].upper()}] {item['title']}: {item['detail']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Actions"])
    if actions:
        for item in actions:
            result = item.get("result") or {}
            rc = result.get("returncode")
            lines.append(f"- {item['key']}: rc={rc} reason={item.get('reason')}")
    else:
        lines.append("- none")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuously summarize weaknesses and run safe repairs")
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = read_json(STATE_PATH, {"cycle": 0})
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "stage": "starting",
        "pid": os.getpid(),
        "cycle": int(state.get("cycle", 0)),
        "pollSeconds": args.poll_seconds,
        "lastRun": state.get("lastRun", {}),
    }
    write_json(STATUS_PATH, status)

    while True:
        status["cycle"] = int(status.get("cycle", 0)) + 1
        status["updatedAt"] = now_jst_text()
        status["stage"] = "evaluate"
        strengths, weaknesses, context = summarize()
        actions = planned_actions(weaknesses)
        status["strengths"] = strengths
        status["weaknesses"] = weaknesses
        status["plannedActions"] = actions
        status["context"] = {
            "learningHealth": context.get("learningHealth"),
            "emailDaemonStage": (context.get("emailDaemon") or {}).get("stage"),
            "emailWatchdogReason": (context.get("emailWatchdog") or {}).get("lastReason"),
            "emailQualityMetrics": (context.get("emailQuality") or {}).get("metrics"),
            "emailIntegrityOk": (context.get("emailIntegrity") or {}).get("ok"),
            "appReadiness": (context.get("appReadiness") or {}).get("readiness"),
            "paperlessIngestAudit": (context.get("paperlessIngestAudit") or {}).get("status"),
            "emailBlacklistHubOk": (context.get("blacklistConfig") or {}).get("ok"),
            "emailBlacklistCandidateCount": len(((context.get("blacklistCandidates") or {}).get("payload") or {}).get("candidates") or []),
            "emailSearchApiOk": (context.get("emailSearchStats") or {}).get("ok"),
            "hostApiInventory": context.get("hostApiInventory"),
            "serviceInventory": context.get("serviceInventory"),
            "gatewayIngestWatchdogCount": context.get("gatewayIngestWatchdogCount"),
            "paperlessAuthProbe": context.get("paperlessAuthProbe"),
            "paperlessTokenRefresh": context.get("paperlessTokenRefresh"),
            "emailPolicyMode": (context.get("emailPolicy") or {}).get("email"),
        }
        write_json(STATUS_PATH, status)

        action_results: list[dict[str, Any]] = []
        if actions:
            status["stage"] = "improve"
            write_json(STATUS_PATH, status)
            for action in actions:
                result = execute_action(action["key"])
                action_results.append({**action, "result": result})
                status["actionResults"] = action_results
                status["updatedAt"] = now_jst_text()
                write_json(STATUS_PATH, status)
        else:
            status["actionResults"] = []

        status["stage"] = "completed"
        status["finishedAt"] = now_jst_text()
        write_json(STATUS_PATH, status)
        write_summary(strengths, weaknesses, action_results)

        state["cycle"] = status["cycle"]
        state["lastRun"] = {
            "finishedAt": status["finishedAt"],
            "weaknessCount": len(weaknesses),
            "actionCount": len(action_results),
        }
        write_json(STATE_PATH, state)

        if args.once:
            break
        time.sleep(max(args.poll_seconds, 60))


if __name__ == "__main__":
    main()
