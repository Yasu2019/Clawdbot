from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path.cwd()
STATUS_PATH = Path(__file__).with_name("prepare_clawstack_unified_native_cutover_status.json")
PROGRESS_JSON_PATH = Path(__file__).with_name("clawstack_unified_native_cutover_progress.json")
PROGRESS_MD_PATH = Path(__file__).with_name("clawstack_unified_native_cutover_progress.md")
MAX_PULL_ATTEMPTS = 3
MAX_BUILD_ATTEMPTS = 2
DEFAULT_PULL_SECONDS = 180
DEFAULT_BUILD_SECONDS = 600

BUILD_SERVICES = [
    "n8n",
    "openradioss",
    "quality_dashboard",
    "minigame_api",
    "minigame_ui",
    "dxf3d_app",
    "workstudy_app",
    "clawdbot-gateway",
]

PULL_SERVICES = [
    "docling",
    "excalidraw",
    "clickhouse",
    "postgres",
    "langfuse-db-init",
    "redis",
    "langfuse",
    "ollama",
    "litellm",
    "nocodb",
    "ntfy",
    "prometheus",
    "grafana",
    "immich_machine_learning",
    "infinity",
    "it-tools",
    "libretranslate",
    "metabase",
    "open_notebook_db",
    "paperless",
    "immich_postgres",
    "immich_redis",
    "immich_server",
    "db_minigame",
    "nodered",
    "open_notebook",
    "qdrant",
    "searxng",
    "open_webui",
    "uptime-kuma",
    "watchtower",
    "crawl4ai",
    "meilisearch",
    "portal_server",
    "whishper-mongo",
    "whishper",
    "dozzle",
    "mailpit",
    "minio",
    "outline",
    "portainer",
    "chrono",
    "stirling_pdf",
    "voicevox",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_existing_status() -> dict[str, Any] | None:
    if not STATUS_PATH.exists():
        return None
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def step_index(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for step in status.get("steps", []):
        name = step.get("name")
        if name:
            index[name] = step
    return index


def init_status() -> dict[str, Any]:
    existing = load_existing_status()
    if existing:
        existing["updatedAt"] = iso_now()
        existing.setdefault("steps", [])
        existing["runtimeTarget"] = "wsl_native"
        existing["phase"] = "prewarm_resume"
        return existing
    return {
        "startedAt": iso_now(),
        "updatedAt": iso_now(),
        "repoRoot": str(REPO_ROOT),
        "runtimeTarget": "wsl_native",
        "phase": "prewarm",
        "buildServices": BUILD_SERVICES,
        "pullServices": PULL_SERVICES,
        "steps": [],
    }


def format_eta(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"about {minutes} min"
    hours = minutes // 60
    rem = minutes % 60
    if rem == 0:
        return f"about {hours} h"
    return f"about {hours} h {rem} min"


def build_progress_summary(status: dict[str, Any]) -> dict[str, Any]:
    steps = step_index(status)
    planned_pulls = [f"pull_{service}" for service in PULL_SERVICES]
    planned_builds = [f"build_{service}" for service in BUILD_SERVICES]
    planned = planned_pulls + planned_builds

    pull_success = [name for name in planned_pulls if steps.get(name, {}).get("returncode") == 0]
    build_success = [name for name in planned_builds if steps.get(name, {}).get("returncode") == 0]
    pull_failed = [name for name in planned_pulls if name in steps and steps[name].get("returncode") != 0]
    build_failed = [name for name in planned_builds if name in steps and steps[name].get("returncode") != 0]
    pending = [name for name in planned if name not in steps or steps[name].get("returncode") != 0]

    pull_durations = [steps[name]["durationSeconds"] for name in pull_success if steps[name].get("durationSeconds")]
    build_durations = [steps[name]["durationSeconds"] for name in build_success if steps[name].get("durationSeconds")]
    avg_pull = sum(pull_durations) / len(pull_durations) if pull_durations else None
    avg_build = sum(build_durations) / len(build_durations) if build_durations else None

    remaining_pulls = len([name for name in planned_pulls if name not in pull_success])
    remaining_builds = len([name for name in planned_builds if name not in build_success])
    effective_pull = avg_pull if avg_pull is not None else DEFAULT_PULL_SECONDS
    effective_build = avg_build if avg_build is not None else DEFAULT_BUILD_SECONDS
    eta_seconds = effective_pull * remaining_pulls + effective_build * remaining_builds

    total = len(planned)
    completed = len(pull_success) + len(build_success)
    percent = round((completed / total) * 100, 1) if total else 100.0
    active_step = status.get("currentStep")
    active_since = status.get("currentStepStartedAt")

    return {
        "updatedAt": status.get("updatedAt"),
        "phase": status.get("phase"),
        "activeStep": active_step,
        "activeStepStartedAt": active_since,
        "totalSteps": total,
        "completedSteps": completed,
        "remainingSteps": total - completed,
        "percentComplete": percent,
        "pulls": {
            "completed": len(pull_success),
            "total": len(planned_pulls),
            "failed": pull_failed,
            "remaining": remaining_pulls,
            "averageSeconds": round(avg_pull, 1) if avg_pull is not None else None,
            "assumedSecondsWhenUnknown": DEFAULT_PULL_SECONDS,
        },
        "builds": {
            "completed": len(build_success),
            "total": len(planned_builds),
            "failed": build_failed,
            "remaining": remaining_builds,
            "averageSeconds": round(avg_build, 1) if avg_build is not None else None,
            "assumedSecondsWhenUnknown": DEFAULT_BUILD_SECONDS,
        },
        "remainingItems": [name.removeprefix("pull_").removeprefix("build_") for name in pending],
        "etaSeconds": round(eta_seconds, 1) if eta_seconds is not None else None,
        "etaLabel": format_eta(eta_seconds),
        "etaBasis": "successful pull/build averages when available, otherwise conservative defaults",
    }


def write_progress_files(status: dict[str, Any]) -> None:
    summary = build_progress_summary(status)
    PROGRESS_JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Clawstack Native Cutover Progress",
        "",
        f"- Updated: `{summary['updatedAt']}`",
        f"- Phase: `{summary['phase']}`",
        f"- Progress: `{summary['completedSteps']} / {summary['totalSteps']}` ({summary['percentComplete']}%)",
        f"- Remaining: `{summary['remainingSteps']}`",
        f"- ETA: `{summary['etaLabel'] or 'calculating'}`",
    ]
    if summary.get("activeStep"):
        lines.append(f"- Current step: `{summary['activeStep']}` since `{summary.get('activeStepStartedAt')}`")
    if summary["remainingItems"]:
        lines.extend(["", "## Remaining items", ""])
        lines.extend([f"- `{item}`" for item in summary["remainingItems"]])
    PROGRESS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(status: dict[str, Any]) -> None:
    status["updatedAt"] = iso_now()
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    write_progress_files(status)


def run_step(name: str, command: list[str], status: dict[str, Any], allow_failure: bool = False) -> bool:
    status["currentStep"] = name
    status["currentStepStartedAt"] = iso_now()
    write_status(status)
    started_at = iso_now()
    started = time.time()
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    step = {
        "name": name,
        "command": command,
        "startedAt": started_at,
        "finishedAt": iso_now(),
        "durationSeconds": round(time.time() - started, 2),
        "returncode": proc.returncode,
        "stdoutTail": proc.stdout[-4000:],
        "stderrTail": proc.stderr[-4000:],
    }
    status.setdefault("steps", []).append(step)
    status["lastCompletedStep"] = name
    status["currentStep"] = None
    status["currentStepStartedAt"] = None
    write_status(status)
    if proc.returncode != 0:
        if allow_failure:
            return False
        raise subprocess.CalledProcessError(proc.returncode, command, output=proc.stdout, stderr=proc.stderr)
    return True


def run_with_retries(
    name: str,
    command: list[str],
    status: dict[str, Any],
    attempts: int,
    allow_failure: bool = False,
) -> bool:
    for attempt in range(1, attempts + 1):
        ok = run_step(name, command, status, allow_failure=True)
        if ok:
            return True
        last_step = status["steps"][-1]
        last_step["attempt"] = attempt
        if attempt < attempts:
            time.sleep(min(20, 5 * attempt))
    if allow_failure:
        return False
    raise subprocess.CalledProcessError(
        status["steps"][-1]["returncode"],
        command,
        output=status["steps"][-1]["stdoutTail"],
        stderr=status["steps"][-1]["stderrTail"],
    )


def main() -> int:
    status = init_status()
    write_status(status)

    base = [
        "wsl",
        "-d",
        "Ubuntu",
        "-u",
        "root",
        "--",
        "bash",
        "-lc",
    ] 

    pull_failures: list[str] = []
    completed = step_index(status)
    for service in PULL_SERVICES:
        if completed.get(f"pull_{service}", {}).get("returncode") == 0:
            continue
        pull_cmd = (
            "cd /mnt/d/Clawdbot_Docker_20260125 && "
            "DOCKER_HOST=unix:///var/run/docker-native.sock "
            f"docker compose pull {service}"
        )
        ok = run_with_retries(
            f"pull_{service}",
            base + [pull_cmd],
            status,
            attempts=MAX_PULL_ATTEMPTS,
            allow_failure=True,
        )
        if not ok:
            pull_failures.append(service)

    build_failures: list[str] = []
    completed = step_index(status)
    for service in BUILD_SERVICES:
        if completed.get(f"build_{service}", {}).get("returncode") == 0:
            continue
        build_cmd = (
            "cd /mnt/d/Clawdbot_Docker_20260125 && "
            "DOCKER_HOST=unix:///var/run/docker-native.sock "
            f"docker compose build {service}"
        )
        ok = run_with_retries(
            f"build_{service}",
            base + [build_cmd],
            status,
            attempts=MAX_BUILD_ATTEMPTS,
            allow_failure=True,
        )
        if not ok:
            build_failures.append(service)

    final_check_cmd = (
        "DOCKER_HOST=unix:///var/run/docker-native.sock docker image ls --format '{{.Repository}}:{{.Tag}}'"
    )
    run_with_retries("native_image_inventory", base + [final_check_cmd], status, attempts=1)

    status["finishedAt"] = iso_now()
    status["pullFailures"] = pull_failures
    status["buildFailures"] = build_failures
    status["ok"] = not pull_failures and not build_failures
    status["phase"] = "prewarm_completed"
    write_status(status)
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
