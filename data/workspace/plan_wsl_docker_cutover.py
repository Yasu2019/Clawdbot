from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent
INVENTORY_PATH = WORKSPACE / "wsl_docker_project_inventory.json"
NATIVE_STATUS_PATH = WORKSPACE / "wsl_native_docker_migration_status.json"
PLAN_JSON_PATH = WORKSPACE / "wsl_docker_cutover_plan.json"
PLAN_MD_PATH = WORKSPACE / "wsl_docker_cutover_plan.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    inventory = load_json(INVENTORY_PATH)
    native_status = load_json(NATIVE_STATUS_PATH)

    desktop_projects = inventory.get("desktop", {}).get("projects", {})
    native_projects = inventory.get("native", {}).get("projects", {})
    plan = {
        "timestamp": ts,
        "nativeDaemonReady": native_status.get("nativeReady", False),
        "cutoverReady": False,
        "phases": [],
    }

    phases = []
    if native_status.get("nativeReady"):
        phases.append(
            {
                "phase": "phase_1_native_daemon_ready",
                "status": "completed",
                "goal": "Independent WSL native docker daemon is running on /var/run/docker-native.sock",
            }
        )
    else:
        phases.append(
            {
                "phase": "phase_1_native_daemon_ready",
                "status": "pending",
                "goal": "Independent WSL native docker daemon must be running before cutover",
            }
        )

    phases.append(
        {
            "phase": "phase_2_inventory_baseline",
            "status": "completed",
            "goal": "Current Docker Desktop projects and services are inventoried",
            "projects": sorted(desktop_projects.keys()),
        }
    )

    migration_projects = []
    for project, payload in desktop_projects.items():
        native_payload = native_projects.get(project, {})
        migrated = bool(native_payload.get("containers"))
        migration_projects.append(
            {
                "project": project,
                "serviceCount": len(payload.get("services", [])),
                "desktopRunningContainers": sum(
                    1 for row in payload.get("containers", []) if str(row.get("status", "")).startswith("Up")
                ),
                "nativeRunningContainers": sum(
                    1 for row in native_payload.get("containers", []) if str(row.get("status", "")).startswith("Up")
                ),
                "status": "completed" if migrated else "pending",
            }
        )

    phases.append(
        {
            "phase": "phase_3_migrate_compose_projects",
            "status": "completed" if all(item["status"] == "completed" for item in migration_projects) else "in_progress",
            "goal": "Recreate compose projects on native daemon without touching desktop runtime yet",
            "projects": migration_projects,
        }
    )

    phases.append(
        {
            "phase": "phase_4_validation",
            "status": "pending",
            "goal": "Portal, Paperless, Gmail, n8n, and quality apps pass smoke checks on native daemon",
        }
    )

    phases.append(
        {
            "phase": "phase_5_runtime_switch",
            "status": "pending",
            "goal": "Switch repo-side runtime helper to wsl_native after services are verified",
            "switchScript": "data/workspace/switch_docker_runtime_to_wsl_native.ps1",
            "rollbackScript": "data/workspace/switch_docker_runtime_to_wsl_desktop.ps1",
        }
    )

    plan["phases"] = phases
    plan["cutoverReady"] = bool(
        native_status.get("nativeReady") and not inventory.get("missingProjectsOnNative")
    )

    PLAN_JSON_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# WSL Docker Cutover Plan",
        "",
        f"- Timestamp: `{ts}`",
        f"- Native daemon ready: `{native_status.get('nativeReady')}`",
        f"- Cutover ready: `{plan['cutoverReady']}`",
        "",
        "## Phases",
        "",
    ]
    for phase in phases:
        lines.append(f"- `{phase['phase']}`: {phase['status']} - {phase['goal']}")
    lines.extend(
        [
            "",
            "## Project migration progress",
            "",
        ]
    )
    for item in migration_projects:
        lines.append(
            f"- `{item['project']}`: {item['status']} "
            f"(desktop running `{item['desktopRunningContainers']}`, native running `{item['nativeRunningContainers']}`)"
        )
    lines.extend(
        [
            "",
            "## Current blocker",
            "",
            "- Native daemon is up, but `clawstack-unified` is not yet recreated on the native socket.",
            "- Do not run the runtime switch yet; it would move host-side maintenance scripts to an empty daemon.",
        ]
    )
    PLAN_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
