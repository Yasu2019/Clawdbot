#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATUS_PATH = ROOT / "openclaw_control_ui_repair_status.json"
CONTAINER = "clawstack-unified-clawdbot-gateway-1"
OPENCLAW_DIR = "/usr/local/lib/node_modules/openclaw"
CONTROL_UI_DIR = f"{OPENCLAW_DIR}/dist/control-ui"
TMP_SRC = "/tmp/openclaw-src"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def write_status(payload: dict) -> None:
    payload = {"updatedAt": now_iso(), **payload}
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def docker_exec(script: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["docker", "exec", CONTAINER, "sh", "-lc", script], check=check)


def read_installed_version() -> str:
    result = docker_exec(
        "sed -n '1,40p' /usr/local/lib/node_modules/openclaw/package.json | "
        "grep '\"version\"' | head -n 1"
    )
    line = result.stdout.strip()
    version = line.split(":")[1].strip().strip('",')
    if not version:
        raise RuntimeError("Could not determine installed openclaw version")
    return version


def control_ui_exists() -> bool:
    result = docker_exec(f"test -f {CONTROL_UI_DIR}/index.html && echo yes || echo no")
    return result.stdout.strip() == "yes"


def repair() -> dict:
    version = read_installed_version()
    tag = f"v{version}"
    write_status(
        {
            "status": "running",
            "container": CONTAINER,
            "openclawVersion": version,
            "tag": tag,
            "step": "check_assets",
        }
    )
    if control_ui_exists():
        return {
            "status": "already_ok",
            "container": CONTAINER,
            "openclawVersion": version,
            "tag": tag,
            "controlUiPath": CONTROL_UI_DIR,
        }

    docker_exec(
        "\n".join(
            [
                "set -e",
                "corepack enable",
                f"rm -rf {TMP_SRC}",
                f"git clone --depth 1 --branch {tag} https://github.com/openclaw/openclaw.git {TMP_SRC}",
                f"cd {TMP_SRC}",
                "pnpm install --frozen-lockfile",
                "pnpm ui:build",
                f"rm -rf {CONTROL_UI_DIR}",
                f"mkdir -p {OPENCLAW_DIR}/dist",
                f"cp -R {TMP_SRC}/dist/control-ui {CONTROL_UI_DIR}",
            ]
        )
    )
    run(["docker", "restart", CONTAINER], check=True)
    verify = control_ui_exists()
    if not verify:
        raise RuntimeError("Control UI assets still missing after repair")
    return {
        "status": "repaired",
        "container": CONTAINER,
        "openclawVersion": version,
        "tag": tag,
        "controlUiPath": CONTROL_UI_DIR,
    }


def main() -> int:
    try:
        result = repair()
        write_status(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except subprocess.CalledProcessError as exc:
        payload = {
            "status": "error",
            "container": CONTAINER,
            "returncode": exc.returncode,
            "stdout": exc.stdout[-4000:] if exc.stdout else "",
            "stderr": exc.stderr[-4000:] if exc.stderr else "",
        }
        write_status(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:  # noqa: BLE001
        payload = {
            "status": "error",
            "container": CONTAINER,
            "message": str(exc),
        }
        write_status(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
