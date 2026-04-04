from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "wsl_native_docker_migration_status.json"
SUMMARY_PATH = WORKSPACE / "wsl_native_docker_migration_summary.md"
INSTALL_SCRIPT_PATH = WORKSPACE / "wsl_native_docker_install.sh"
SWITCH_SCRIPT_PATH = WORKSPACE / "switch_docker_runtime_to_wsl_native.ps1"
ROLLBACK_SCRIPT_PATH = WORKSPACE / "switch_docker_runtime_to_wsl_desktop.ps1"
DAEMON_CONFIG_PATH = WORKSPACE / "docker-native-daemon.json"
SERVICE_PATH = WORKSPACE / "docker-native.service"
ENV_PATH = WORKSPACE / "docker-native.env"

DISTRO = "Ubuntu"
NATIVE_SOCKET = "/var/run/docker-native.sock"
NATIVE_DATA_ROOT = "/var/lib/docker-native"


def run_command(*args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def run_wsl(script: str) -> tuple[int, str, str]:
    return run_command("wsl", "-d", DISTRO, "--", "bash", "-lc", script)


def write_utf8(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def build_status() -> dict:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    status: dict = {
        "timestamp": ts,
        "distro": DISTRO,
        "nativeSocket": NATIVE_SOCKET,
        "nativeDataRoot": NATIVE_DATA_ROOT,
    }

    rc, out, err = run_wsl("systemctl is-active docker")
    status["dockerServiceActive"] = out if rc == 0 else None
    status["dockerServiceCheckError"] = err if rc != 0 else None

    rc, out, err = run_wsl("systemctl is-system-running || true")
    status["systemdState"] = out.splitlines()[0] if out else None
    status["systemdCheckError"] = err or None

    rc, out, err = run_wsl("sudo -n true >/dev/null 2>&1; printf '__RC__:%s' \"$?\"")
    probe = out.strip()
    status["passwordlessSudoReady"] = probe.endswith("__RC__:0")
    status["passwordlessSudoProbeRaw"] = probe
    status["passwordlessSudoProbeError"] = err or None

    rc, out, err = run_wsl(
        "printf 'dockerd-rootless-setuptool=%s\\nrootlesskit=%s\\nslirp4netns=%s\\n' "
        "\"$(command -v dockerd-rootless-setuptool.sh || true)\" "
        "\"$(command -v rootlesskit || true)\" "
        "\"$(command -v slirp4netns || true)\""
    )
    tools: dict[str, str | None] = {}
    for line in out.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            tools[key] = value or None
    status["rootlessTools"] = tools
    status["rootlessToolsCheckError"] = err or None

    rc, out, err = run_wsl(
        "systemctl list-units --all | grep -E 'mnt-wsl-docker|docker-native|docker\\.service|docker\\.socket' || true"
    )
    status["unitHints"] = out.splitlines()
    status["unitHintsError"] = err or None

    rc, out, err = run_wsl(
        "test -S /var/run/docker.sock && echo docker.sock=yes || echo docker.sock=no; "
        "test -S /var/run/docker-native.sock && echo docker-native.sock=yes || echo docker-native.sock=no"
    )
    socket_map: dict[str, bool] = {}
    for line in out.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            socket_map[key] = value == "yes"
    status["socketPresence"] = socket_map
    status["socketPresenceError"] = err or None

    rc, out, err = run_wsl("docker info --format '{{.ServerVersion}}|{{.DockerRootDir}}|{{.Name}}' 2>/dev/null || true")
    if out:
        parts = out.split("|")
        status["currentDockerInfo"] = {
            "serverVersion": parts[0] if len(parts) > 0 else None,
            "dockerRootDir": parts[1] if len(parts) > 1 else None,
            "name": parts[2] if len(parts) > 2 else None,
        }
    else:
        status["currentDockerInfo"] = None
    status["currentDockerInfoError"] = err or None

    status["nativeReady"] = bool(
        status["passwordlessSudoReady"]
        and socket_map.get("docker-native.sock", False)
    )
    status["blockers"] = []
    if not status["passwordlessSudoReady"]:
        status["blockers"].append("Ubuntu sudo still requires an interactive password.")
    if tools.get("rootlesskit") is None:
        status["blockers"].append("Rootless Docker helper tools are not installed.")
    if any("docker.sock.mount" in line for line in status.get("unitHints", [])):
        status["blockers"].append("Current Ubuntu docker socket is still backed by Docker Desktop mount.")
    status["recommendedNextStep"] = (
        "activate_native_runtime"
        if status["nativeReady"]
        else "run_install_script_inside_ubuntu_with_sudo"
    )
    return status


def build_install_script() -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

NATIVE_SOCKET="{NATIVE_SOCKET}"
NATIVE_DATA_ROOT="{NATIVE_DATA_ROOT}"
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

sudo mkdir -p "$NATIVE_DATA_ROOT"
sudo cp "$SCRIPT_DIR/docker-native-daemon.json" /etc/docker/daemon-native.json
sudo cp "$SCRIPT_DIR/docker-native.env" /etc/default/docker-native
sudo cp "$SCRIPT_DIR/docker-native.service" /etc/systemd/system/docker-native.service
sudo systemctl daemon-reload
sudo systemctl enable docker-native.service
sudo systemctl restart docker-native.service
sudo systemctl --no-pager --full status docker-native.service || true
sudo test -S "$NATIVE_SOCKET"
DOCKER_HOST="unix://$NATIVE_SOCKET" docker version
"""


def build_daemon_config() -> str:
    return json.dumps(
        {
            "data-root": NATIVE_DATA_ROOT,
            "hosts": [f"unix://{NATIVE_SOCKET}"],
            "iptables": True,
            "features": {"buildkit": True},
            "log-driver": "json-file",
            "log-opts": {"max-size": "10m", "max-file": "3"},
            "storage-driver": "overlay2",
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def build_env_file() -> str:
    return 'DOCKERD_EXTRA_ARGS="--config-file /etc/docker/daemon-native.json --pidfile /var/run/docker-native.pid"\n'


def build_service_file() -> str:
    return """[Unit]
Description=Independent Docker Engine for headless WSL operation
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
EnvironmentFile=-/etc/default/docker-native
ExecStart=/usr/bin/dockerd $DOCKERD_EXTRA_ARGS
ExecReload=/bin/kill -s HUP $MAINPID
TimeoutStartSec=0
Restart=always
RestartSec=2
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process

[Install]
WantedBy=multi-user.target
"""


def build_switch_script(mode: str, socket_path: str) -> str:
    runtime_mode = "wsl_native" if mode == "native" else "wsl_desktop"
    return f"""[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$configPath = Join-Path $repoRoot "data\\workspace\\docker_runtime_config.json"

@'
{{
  "mode": "{runtime_mode}",
  "wslDistro": "{DISTRO}",
  "wslSocketPath": "{socket_path}"
}}
'@ | Set-Content -LiteralPath $configPath -Encoding UTF8

Get-Content -LiteralPath $configPath
"""


def build_summary(status: dict) -> str:
    lines = [
        "# WSL Native Docker Migration Prep",
        "",
        f"- Timestamp: `{status['timestamp']}`",
        f"- Distro: `{status['distro']}`",
        f"- Current runtime: `{(status.get('currentDockerInfo') or {}).get('name')}`",
        f"- Current docker root: `{(status.get('currentDockerInfo') or {}).get('dockerRootDir')}`",
        f"- Passwordless sudo ready: `{status['passwordlessSudoReady']}`",
        f"- Native socket exists: `{status.get('socketPresence', {}).get('docker-native.sock')}`",
        f"- Current desktop socket exists: `{status.get('socketPresence', {}).get('docker.sock')}`",
        "",
        "## Coupling hints",
        "",
    ]
    for unit in status.get("unitHints", []):
        lines.append(f"- `{unit}`")
    lines.extend(
        [
            "",
            "## Ready artifacts",
            "",
            f"- Installer script: `{INSTALL_SCRIPT_PATH.name}`",
            f"- Native daemon config: `{DAEMON_CONFIG_PATH.name}`",
            f"- systemd unit: `{SERVICE_PATH.name}`",
            f"- Runtime switch to native: `{SWITCH_SCRIPT_PATH.name}`",
            f"- Runtime rollback to desktop socket: `{ROLLBACK_SCRIPT_PATH.name}`",
            "",
            "## Recommended next step",
            "",
            f"- `{status['recommendedNextStep']}`",
        ]
    )
    if not status["passwordlessSudoReady"]:
        lines.extend(
            [
                "",
                "## Note",
                "",
                "- Ubuntu still requires a password for `sudo`, so the installer must be run manually inside WSL once.",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    status = build_status()
    write_utf8(INSTALL_SCRIPT_PATH, build_install_script())
    write_utf8(DAEMON_CONFIG_PATH, build_daemon_config())
    write_utf8(ENV_PATH, build_env_file())
    write_utf8(SERVICE_PATH, build_service_file())
    write_utf8(SWITCH_SCRIPT_PATH, build_switch_script("native", NATIVE_SOCKET))
    write_utf8(ROLLBACK_SCRIPT_PATH, build_switch_script("desktop", "/var/run/docker.sock"))
    write_utf8(SUMMARY_PATH, build_summary(status))
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
