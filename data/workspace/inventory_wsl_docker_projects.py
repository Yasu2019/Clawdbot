from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "wsl_docker_project_inventory.json"
SUMMARY_PATH = WORKSPACE / "wsl_docker_project_inventory.md"
DISTRO = "Ubuntu"


def run_wsl(script: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["wsl", "-d", DISTRO, "--", "bash", "-lc", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def list_containers(socket_path: str | None) -> list[dict]:
    host_prefix = f"DOCKER_HOST=unix://{socket_path} " if socket_path else ""
    fmt = '{{json .}}'
    script = f"{host_prefix}docker ps -a --format '{fmt}'"
    rc, out, err = run_wsl(script)
    if rc != 0:
        raise RuntimeError(err or out or f"docker ps failed for {socket_path or 'desktop'}")
    rows: list[dict] = []
    for line in out.splitlines():
        payload = json.loads(line)
        labels_raw = str(payload.get("Labels") or "")
        label_map: dict[str, str] = {}
        for chunk in labels_raw.split(","):
            if "=" in chunk:
                key, value = chunk.split("=", 1)
                label_map[key.strip()] = value.strip()
        rows.append(
            {
                "name": str(payload.get("Names") or ""),
                "project": label_map.get("com.docker.compose.project", ""),
                "service": label_map.get("com.docker.compose.service", ""),
                "status": str(payload.get("Status") or ""),
            }
        )
    return rows


def group_projects(rows: list[dict]) -> dict[str, dict]:
    grouped: dict[str, dict] = defaultdict(lambda: {"services": [], "containers": []})
    for row in rows:
        project = row["project"] or "_unlabeled"
        if row["service"] and row["service"] not in grouped[project]["services"]:
            grouped[project]["services"].append(row["service"])
        grouped[project]["containers"].append(row)
    return dict(grouped)


def main() -> int:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    desktop_rows = list_containers(None)
    native_rows = list_containers("/var/run/docker-native.sock")
    desktop_projects = group_projects(desktop_rows)
    native_projects = group_projects(native_rows)

    missing_projects = sorted(set(desktop_projects) - set(native_projects))
    status = {
        "timestamp": ts,
        "desktop": {
            "containerCount": len(desktop_rows),
            "projectCount": len(desktop_projects),
            "projects": desktop_projects,
        },
        "native": {
            "containerCount": len(native_rows),
            "projectCount": len(native_projects),
            "projects": native_projects,
        },
        "missingProjectsOnNative": missing_projects,
        "nativeReadyForCutover": len(missing_projects) == 0 and len(desktop_rows) > 0,
    }

    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# WSL Docker Project Inventory",
        "",
        f"- Timestamp: `{ts}`",
        f"- Desktop projects: `{len(desktop_projects)}`",
        f"- Native projects: `{len(native_projects)}`",
        f"- Missing on native: `{len(missing_projects)}`",
        "",
        "## Missing projects on native",
        "",
    ]
    for project in missing_projects[:50]:
        services = ", ".join(desktop_projects[project]["services"][:12])
        lines.append(f"- `{project}`: {services}")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
