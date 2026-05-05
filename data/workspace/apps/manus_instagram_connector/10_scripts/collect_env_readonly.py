"""
Read-only environment collector.
Does not print secret values.
Does not modify files.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime

CANDIDATE_ROOTS = [
    Path(r"D:\Clawdbot_Docker_20260125"),
    Path(r"D:\Clawdbot_Docker_20260125\clawstack_v2"),
    Path.cwd(),
]

SECRET_HINTS = ["KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "CREDENTIAL"]

def run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
        return (out.stdout or out.stderr or "").strip()
    except Exception as exc:
        return f"ERROR: {exc}"

def mask_env() -> dict[str, str]:
    result = {}
    for k, v in os.environ.items():
        if any(h in k.upper() for h in SECRET_HINTS):
            result[k] = "***MASKED***"
        else:
            result[k] = v
    return result

def main() -> None:
    report = {
        "timestamp": datetime.now().isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "candidate_roots": {str(p): p.exists() for p in CANDIDATE_ROOTS},
        "docker_version": run(["docker", "--version"]),
        "docker_ps": run(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]),
        "docker_volumes": run(["docker", "volume", "ls"]),
        "docker_networks": run(["docker", "network", "ls"]),
        "compose_files": [],
        "env_files_exist": [],
        "env_names_masked": mask_env(),
    }

    for root in CANDIDATE_ROOTS:
        if root.exists():
            for pattern in ["docker-compose*.yml", "compose*.yml", "*.compose.yml"]:
                report["compose_files"].extend(str(p) for p in root.rglob(pattern))
            for p in root.rglob(".env*"):
                report["env_files_exist"].append(str(p))

    out = Path("openclaw_env_readonly_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote read-only report: {out.resolve()}")

if __name__ == "__main__":
    main()
