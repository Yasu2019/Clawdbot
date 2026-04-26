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

from docker_runtime import docker_command

JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).absolute().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "paperless_rag_watchdog_status.json"
STATE_PATH = WORKSPACE / "paperless_rag_watchdog_state.json"
HARNESS_PATH = ROOT / "data" / "state" / "paperless_rag_watchdog" / "harness_status.json"
INGEST_STATUS_PATH = WORKSPACE / "ingest_watchdog_status.json"
REVIEW_ARTIFACT_STATUS_PATH = WORKSPACE / "paperless_pdf_review_artifacts_status.json"
INGEST_AUDIT_STATUS_PATH = WORKSPACE / "paperless_ingest_audit_status.json"
GATEWAY_CONTAINER = "clawstack-unified-clawdbot-gateway-1"
INGEST_PID = "/home/node/clawd/ingest_watchdog.pid"
INGEST_LOG = "/home/node/clawd/ingest_watchdog.log"
INGEST_SCRIPT = "/home/node/clawd/ingest_watchdog.py"
REVIEW_ARTIFACT_SCRIPT = WORKSPACE / "update_paperless_pdf_review_artifacts.py"
INGEST_AUDIT_SCRIPT = WORKSPACE / "audit_paperless_ingest_alignment.py"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


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


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_command(command: list[str], timeout_seconds: int = 60) -> dict[str, Any]:
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


def container_is_running() -> bool:
    result = run_command(
        docker_command(
            "ps",
            "--filter",
            f"name={GATEWAY_CONTAINER}",
            "--filter",
            "status=running",
            "--format",
            "{{.Names}}",
        ),
        30,
    )
    names = [line.strip() for line in result.get("stdout", "").splitlines() if line.strip()]
    return GATEWAY_CONTAINER in names


def gateway_container_state() -> dict[str, Any]:
    result = run_command(
        docker_command(
            "inspect",
            GATEWAY_CONTAINER,
            "--format",
            "{{json .State}}",
        ),
        30,
    )
    if result.get("returncode") != 0:
        return {}
    try:
        payload = json.loads(result.get("stdout") or "{}")
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def ingest_process_alive() -> bool:
    result = run_command(
        docker_command(
            "exec",
            GATEWAY_CONTAINER,
            "sh",
            "-lc",
            "pgrep -f '^python3 /home/node/clawd/ingest_watchdog.py$' >/dev/null",
        ),
        30,
    )
    return result.get("returncode") == 0


def ingest_process_count() -> int:
    result = run_command(
        docker_command(
            "exec",
            GATEWAY_CONTAINER,
            "sh",
            "-lc",
            "pgrep -fc '^python3 /home/node/clawd/ingest_watchdog.py$' || true",
        ),
        30,
    )
    try:
        return int(str(result.get("stdout") or "").strip() or "0")
    except Exception:
        return 0


def restart_ingest() -> dict[str, Any]:
    script = (
        "pkill -f '^python3 /home/node/clawd/ingest_watchdog.py$' || true; "
        "sleep 1; "
        f'rm -f "{INGEST_PID}"; '
        f'nohup python3 "{INGEST_SCRIPT}" >> "{INGEST_LOG}" 2>&1 </dev/null &'
    )
    return run_command(docker_command("exec", GATEWAY_CONTAINER, "sh", "-lc", script), 60)


def should_notify(state: dict[str, Any], key: str, cooldown_minutes: int) -> bool:
    sent = (state.get("notifications") or {}).get(key, {})
    sent_at = parse_dt(sent.get("sentAt"))
    if sent_at is None:
        return True
    return (now_jst().astimezone(sent_at.tzinfo) - sent_at) >= timedelta(minutes=cooldown_minutes)


def remember_notification(state: dict[str, Any], key: str, detail: str) -> None:
    state.setdefault("notifications", {})
    state["notifications"][key] = {"sentAt": now_jst_text(), "detail": detail}


def write_harness(status: dict[str, Any]) -> None:
    payload = {
        "updatedAt": status.get("updatedAt"),
        "service": "paperless_rag_watchdog",
        "state": status.get("stage"),
        "reason": status.get("lastReason"),
        "lastAction": status.get("lastAction"),
        "containerRunning": status.get("containerRunning"),
        "ingestAlive": status.get("ingestAlive"),
    }
    save_json(HARNESS_PATH, payload)


def refresh_review_artifacts(reason: str, review_limit: int, benchmark_limit: int) -> dict[str, Any]:
    return run_command(
        [
            "python",
            str(REVIEW_ARTIFACT_SCRIPT),
            "--review-limit",
            str(review_limit),
            "--benchmark-limit",
            str(benchmark_limit),
            "--reason",
            reason,
        ],
        360,
    )


def refresh_ingest_audit(recent_limit: int) -> dict[str, Any]:
    return run_command(
        [
            "python",
            str(INGEST_AUDIT_SCRIPT),
            "--recent-limit",
            str(recent_limit),
        ],
        180,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchdog for Paperless -> Qdrant ingest and OpenClaw retrieval")
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument("--stale-minutes", type=int, default=15)
    parser.add_argument("--notify-cooldown-minutes", type=int, default=30)
    parser.add_argument("--review-limit", type=int, default=8)
    parser.add_argument("--benchmark-limit", type=int, default=12)
    parser.add_argument("--review-refresh-minutes", type=int, default=180)
    parser.add_argument("--audit-recent-limit", type=int, default=10)
    parser.add_argument("--audit-refresh-minutes", type=int, default=180)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = load_json(STATE_PATH, {})
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "stage": "running",
        "pid": os.getpid(),
        "lastReason": "",
        "lastAction": "",
        "containerRunning": False,
        "ingestAlive": False,
        "lastIngestStatus": {},
    }

    while True:
        ingest_status = load_json(INGEST_STATUS_PATH, {})
        updated = parse_dt(ingest_status.get("updatedAt"))
        stage = str(ingest_status.get("stage") or "")
        age_minutes = None
        if updated is not None:
            age_minutes = round((now_jst().astimezone(updated.tzinfo) - updated).total_seconds() / 60.0, 1)

        container_running = container_is_running()
        container_state = gateway_container_state() if container_running else {}
        ingest_alive = container_running and ingest_process_alive()
        ingest_count = ingest_process_count() if container_running else 0

        healthy = True
        reason = "healthy"
        warmup = False
        warmup_reason = ""
        started_at = parse_dt(container_state.get("StartedAt"))
        running_for_minutes = None
        if started_at is not None:
            running_for_minutes = round(
                (now_jst().astimezone(started_at.tzinfo) - started_at).total_seconds() / 60.0,
                1,
            )
        if not container_running:
            healthy = False
            reason = "gateway container is not running"
        elif running_for_minutes is not None and running_for_minutes < 3.0 and not ingest_alive:
            warmup = True
            warmup_reason = f"gateway container warm-up ({running_for_minutes} minutes since start)"
        elif not ingest_alive:
            healthy = False
            reason = "ingest_watchdog.py is not running inside gateway"
        elif ingest_count > 1:
            healthy = False
            reason = f"ingest_watchdog.py has duplicate processes ({ingest_count})"
        elif updated is None:
            healthy = False
            reason = "ingest heartbeat is missing"
        elif age_minutes is not None and age_minutes > args.stale_minutes:
            healthy = False
            reason = f"ingest heartbeat stale ({age_minutes} minutes)"
        elif stage == "error":
            healthy = False
            reason = "ingest_watchdog reported error state"

        status["updatedAt"] = now_jst_text()
        status["containerRunning"] = container_running
        status["containerState"] = {
            "status": container_state.get("Status"),
            "startedAt": container_state.get("StartedAt"),
            "runningForMinutes": running_for_minutes,
        }
        status["ingestAlive"] = ingest_alive
        status["ingestProcessCount"] = ingest_count
        status["lastIngestStatus"] = ingest_status
        status["lastReason"] = warmup_reason if warmup else reason
        status["stage"] = "warming_up" if warmup else ("healthy" if healthy else "repairing")
        status["lastAction"] = ""
        save_json(STATUS_PATH, status)
        write_harness(status)

        if warmup:
            pass
        elif not healthy and container_running:
            status["lastAction"] = "restart_ingest_watchdog"
            status["restartResult"] = restart_ingest()
            save_json(STATUS_PATH, status)
            write_harness(status)
            if should_notify(state, "paperless_rag_watchdog_restart", args.notify_cooldown_minutes):
                remember_notification(state, "paperless_rag_watchdog_restart", reason)
                save_json(STATE_PATH, state)
        elif not healthy:
            if should_notify(state, "paperless_rag_gateway_down", args.notify_cooldown_minutes):
                remember_notification(state, "paperless_rag_gateway_down", reason)
                save_json(STATE_PATH, state)
        else:
            review_status = load_json(REVIEW_ARTIFACT_STATUS_PATH, {})
            review_updated = parse_dt(review_status.get("updatedAt"))
            review_age_minutes = None
            if review_updated is not None:
                review_age_minutes = round((now_jst().astimezone(review_updated.tzinfo) - review_updated).total_seconds() / 60.0, 1)
            last_refresh_source_updated = str((state.get("reviewArtifacts") or {}).get("lastIngestUpdatedAt") or "")
            current_ingest_updated = str(ingest_status.get("updatedAt") or "")
            last_refresh_processed = (state.get("reviewArtifacts") or {}).get("lastProcessedCount")
            current_processed = ingest_status.get("processedCount")
            should_refresh = (
                current_ingest_updated and current_ingest_updated != last_refresh_source_updated
            ) or (
                current_processed is not None and current_processed != last_refresh_processed
            ) or (
                review_age_minutes is None or review_age_minutes > args.review_refresh_minutes
            )
            if should_refresh:
                status["lastAction"] = "refresh_paperless_review_artifacts"
                status["reviewArtifactsRefreshResult"] = refresh_review_artifacts(
                    reason="ingest_progress",
                    review_limit=args.review_limit,
                    benchmark_limit=args.benchmark_limit,
                )
                save_json(STATUS_PATH, status)
                if status["reviewArtifactsRefreshResult"].get("returncode") == 0:
                    state.setdefault("reviewArtifacts", {})
                    state["reviewArtifacts"]["lastIngestUpdatedAt"] = current_ingest_updated
                    state["reviewArtifacts"]["lastProcessedCount"] = current_processed
                    state["reviewArtifacts"]["lastRefreshedAt"] = now_jst_text()
                    save_json(STATE_PATH, state)

            audit_status = load_json(INGEST_AUDIT_STATUS_PATH, {})
            audit_updated = parse_dt(audit_status.get("updatedAt"))
            audit_age_minutes = None
            if audit_updated is not None:
                audit_age_minutes = round((now_jst().astimezone(audit_updated.tzinfo) - audit_updated).total_seconds() / 60.0, 1)
            last_audit_source_updated = str((state.get("ingestAudit") or {}).get("lastIngestUpdatedAt") or "")
            current_ingest_updated = str(ingest_status.get("updatedAt") or "")
            should_refresh_audit = (
                current_ingest_updated and current_ingest_updated != last_audit_source_updated
            ) or (
                audit_age_minutes is None or audit_age_minutes > args.audit_refresh_minutes
            )
            if should_refresh_audit:
                status["lastAction"] = "refresh_paperless_ingest_audit"
                status["ingestAuditRefreshResult"] = refresh_ingest_audit(args.audit_recent_limit)
                save_json(STATUS_PATH, status)
                if status["ingestAuditRefreshResult"].get("returncode") == 0:
                    state.setdefault("ingestAudit", {})
                    state["ingestAudit"]["lastIngestUpdatedAt"] = current_ingest_updated
                    state["ingestAudit"]["lastRefreshedAt"] = now_jst_text()
                    save_json(STATE_PATH, state)

        if args.once:
            break
        time.sleep(max(30, args.poll_seconds))


if __name__ == "__main__":
    main()
