from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PATH = Path(__file__).with_name("prepare_clawstack_unified_native_cutover_status.json")
PROGRESS_JSON_PATH = Path(__file__).with_name("clawstack_unified_native_cutover_progress.json")
PROGRESS_MD_PATH = Path(__file__).with_name("clawstack_unified_native_cutover_progress.md")
DEFAULT_PULL_SECONDS = 180
DEFAULT_BUILD_SECONDS = 600


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_status() -> dict[str, Any]:
    return json.loads(STATUS_PATH.read_text(encoding="utf-8"))


def step_index(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for step in status.get("steps", []):
        name = step.get("name")
        if name:
            index[name] = step
    return index


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


def build_summary(status: dict[str, Any]) -> dict[str, Any]:
    pull_services = status.get("pullServices", [])
    build_services = status.get("buildServices", [])
    steps = step_index(status)
    planned_pulls = [f"pull_{service}" for service in pull_services]
    planned_builds = [f"build_{service}" for service in build_services]

    pull_success = [name for name in planned_pulls if steps.get(name, {}).get("returncode") == 0]
    build_success = [name for name in planned_builds if steps.get(name, {}).get("returncode") == 0]
    pull_failed = [name for name in planned_pulls if name in steps and steps[name].get("returncode") != 0]
    build_failed = [name for name in planned_builds if name in steps and steps[name].get("returncode") != 0]
    pending = [
        name for name in (planned_pulls + planned_builds)
        if steps.get(name, {}).get("returncode") != 0
    ]

    pull_durations = [steps[name]["durationSeconds"] for name in pull_success if steps[name].get("durationSeconds")]
    build_durations = [steps[name]["durationSeconds"] for name in build_success if steps[name].get("durationSeconds")]
    avg_pull = sum(pull_durations) / len(pull_durations) if pull_durations else None
    avg_build = sum(build_durations) / len(build_durations) if build_durations else None

    remaining_pulls = len([name for name in planned_pulls if name not in pull_success])
    remaining_builds = len([name for name in planned_builds if name not in build_success])
    effective_pull = avg_pull if avg_pull is not None else DEFAULT_PULL_SECONDS
    effective_build = avg_build if avg_build is not None else DEFAULT_BUILD_SECONDS
    eta_seconds = effective_pull * remaining_pulls + effective_build * remaining_builds

    total = len(planned_pulls) + len(planned_builds)
    completed = len(pull_success) + len(build_success)

    return {
        "updatedAt": iso_now(),
        "sourceUpdatedAt": status.get("updatedAt"),
        "phase": status.get("phase"),
        "activeStep": status.get("currentStep"),
        "activeStepStartedAt": status.get("currentStepStartedAt"),
        "lastCompletedStep": status.get("lastCompletedStep"),
        "totalSteps": total,
        "completedSteps": completed,
        "remainingSteps": total - completed,
        "percentComplete": round((completed / total) * 100, 1) if total else 100.0,
        "pulls": {
            "completed": len(pull_success),
            "total": len(planned_pulls),
            "remaining": remaining_pulls,
            "averageSeconds": round(avg_pull, 1) if avg_pull is not None else None,
            "assumedSecondsWhenUnknown": DEFAULT_PULL_SECONDS,
            "failed": pull_failed,
        },
        "builds": {
            "completed": len(build_success),
            "total": len(planned_builds),
            "remaining": remaining_builds,
            "averageSeconds": round(avg_build, 1) if avg_build is not None else None,
            "assumedSecondsWhenUnknown": DEFAULT_BUILD_SECONDS,
            "failed": build_failed,
        },
        "remainingItems": [name.removeprefix("pull_").removeprefix("build_") for name in pending],
        "etaSeconds": round(eta_seconds, 1) if eta_seconds is not None else None,
        "etaLabel": format_eta(eta_seconds),
        "etaBasis": "successful pull/build averages when available, otherwise conservative defaults",
    }


def write_outputs(summary: dict[str, Any]) -> None:
    PROGRESS_JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Clawstack Native Cutover Progress",
        "",
        f"- Updated: `{summary['updatedAt']}`",
        f"- Source status updated: `{summary['sourceUpdatedAt']}`",
        f"- Progress: `{summary['completedSteps']} / {summary['totalSteps']}` ({summary['percentComplete']}%)",
        f"- Remaining: `{summary['remainingSteps']}`",
        f"- ETA: `{summary['etaLabel'] or 'calculating'}`",
        f"- ETA basis: `{summary['etaBasis']}`",
    ]
    if summary.get("activeStep"):
        lines.append(f"- Current step: `{summary['activeStep']}` since `{summary['activeStepStartedAt']}`")
    elif summary.get("lastCompletedStep"):
        lines.append(f"- Last completed step: `{summary['lastCompletedStep']}`")
    lines.extend(["", "## Remaining items", ""])
    if summary["remainingItems"]:
        lines.extend([f"- `{item}`" for item in summary["remainingItems"]])
    else:
        lines.append("- none")
    PROGRESS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    summary = build_summary(load_status())
    write_outputs(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
