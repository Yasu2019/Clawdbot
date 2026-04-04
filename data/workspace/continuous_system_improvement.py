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
ROOT = WORKSPACE.parent.parent

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
EMAIL_INTEGRITY_STATUS = WORKSPACE / "email_search_integrity_status.json"
APP_IMPROVEMENT_READINESS_STATUS = WORKSPACE / "app_improvement_readiness_status.json"
LEARNING_REPAIR_STATUS = WORKSPACE / "repair_learning_engine_status.json"
PAPERLESS_RAG_WATCHDOG_STATUS = WORKSPACE / "paperless_rag_watchdog_status.json"
PAPERLESS_INGEST_STATUS = WORKSPACE / "ingest_watchdog_status.json"
PAPERLESS_REVIEW_ARTIFACT_STATUS = WORKSPACE / "paperless_pdf_review_artifacts_status.json"
PAPERLESS_INGEST_AUDIT_STATUS = WORKSPACE / "paperless_ingest_audit_status.json"
DOCKER_DESKTOP_UI_WATCHDOG_STATUS = WORKSPACE / "docker_desktop_ui_watchdog_status.json"

START_EMAIL_WATCHDOG = ROOT / "scripts" / "start_email_continuous_watchdog.ps1"
START_DOCKER_UI_WATCHDOG = ROOT / "scripts" / "start_docker_desktop_ui_watchdog.ps1"
LEARNING_HEALTH_URLS = [
    "http://localhost:8110/health",
    "http://127.0.0.1:8110/health",
    "http://host.docker.internal:8110/health",
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
    docker_ui_watchdog = read_json(DOCKER_DESKTOP_UI_WATCHDOG_STATUS, {})
    email_policy = read_json(EMAIL_POLICY_PATH, {})
    learning = learning_health()

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

    if learning.get("ok"):
        strengths.append({"key": "learning_engine", "title": "Learning engine health endpoint is reachable", "detail": f"url={learning.get('url')} collections={learning.get('collections')}"})
    else:
        repair_age_ok, repair_age, _ = status_health(learning_repair, ["finishedAt", "startedAt"], 180)
        repair_detail = "all configured health URLs failed"
        if learning_repair:
            repair_detail = f"all configured health URLs failed; lastRepairResult={learning_repair.get('result')} repairAgeMinutes={repair_age if repair_age_ok else repair_age}"
        weaknesses.append({"key": "learning_engine", "severity": "high", "title": "Learning engine health endpoint is offline", "detail": repair_detail})

    paperless_watchdog_ok, paperless_watchdog_age, paperless_watchdog_state = status_health(paperless_watchdog, ["updatedAt"], 20)
    if paperless_watchdog_ok and str(paperless_watchdog.get("stage") or "") in {"healthy", "running"}:
        strengths.append({"key": "paperless_rag_watchdog", "title": "Paperless RAG watchdog is active", "detail": f"updated {paperless_watchdog_age} minutes ago"})
    else:
        weaknesses.append({"key": "paperless_rag_watchdog", "severity": "high", "title": "Paperless RAG watchdog is stale", "detail": f"state={paperless_watchdog_state} ageMinutes={paperless_watchdog_age}"})

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
    if paperless_audit_ok and str(paperless_ingest_audit.get("status") or "") == "healthy":
        strengths.append({"key": "paperless_ingest_audit", "title": "Paperless ingest audit confirms recent documents are indexed", "detail": f"age={paperless_audit_age} minutes"})
    else:
        missing = len(paperless_ingest_audit.get("recentMissing") or [])
        weaknesses.append({"key": "paperless_ingest_audit", "severity": "high", "title": "Paperless ingest audit found lag or is stale", "detail": f"state={paperless_audit_state} status={paperless_ingest_audit.get('status')} recentMissing={missing}"})

    docker_ui_ok, docker_ui_age, docker_ui_state = status_health(docker_ui_watchdog, ["updatedAt"], 30)
    docker_ui_stage = str(docker_ui_watchdog.get("stage") or "")
    if docker_ui_ok and docker_ui_stage in {"healthy", "starting"} and process_exists("docker_desktop_ui_watchdog.py"):
        strengths.append({"key": "docker_desktop_ui_watchdog", "title": "Docker Desktop UI watchdog is active", "detail": f"stage={docker_ui_stage} age={docker_ui_age} minutes"})
    else:
        weaknesses.append({"key": "docker_desktop_ui_watchdog", "severity": "medium", "title": "Docker Desktop UI watchdog is stale or missing", "detail": f"state={docker_ui_state} stage={docker_ui_stage or 'unknown'} ageMinutes={docker_ui_age}"})

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

    integrity_ok, integrity_age, integrity_state = status_health(email_integrity, ["finishedAt", "startedAt"], 720)
    if integrity_ok and bool(email_integrity.get("ok")):
        strengths.append({"key": "email_integrity", "title": "Email SQLite integrity check is recent", "detail": f"age={integrity_age} minutes"})
    else:
        weaknesses.append({"key": "email_integrity", "severity": "high", "title": "Email SQLite integrity check failed or is stale", "detail": f"state={integrity_state} ok={email_integrity.get('ok')}"})

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
        "emailPolicy": email_policy,
        "learningHealth": learning,
    }
    return strengths, weaknesses, context


def planned_actions(weaknesses: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    weakness_keys = {item["key"] for item in weaknesses}
    if "email_watchdog" in weakness_keys:
        actions.append({"key": "start_email_watchdog", "reason": "Email watchdog is missing or stale"})
    if "docker_desktop_ui_watchdog" in weakness_keys:
        actions.append({"key": "start_docker_desktop_ui_watchdog", "reason": "Docker Desktop UI watchdog is missing or stale"})
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
