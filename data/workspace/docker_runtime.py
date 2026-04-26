from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parent
CONFIG_PATH = WORKSPACE / "docker_runtime_config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "wsl_desktop",
    "wslDistro": "Ubuntu",
    "wslSocketPath": "/var/run/docker.sock",
    "wslUseSystemLauncher": True,
}


def _wsl_prefix(cfg: dict[str, Any]) -> list[str]:
    distro = str(cfg.get("wslDistro") or DEFAULT_CONFIG["wslDistro"])
    use_system = bool(cfg.get("wslUseSystemLauncher", DEFAULT_CONFIG["wslUseSystemLauncher"]))
    prefix = ["wsl"]
    if use_system:
        prefix.append("--system")
    prefix.extend(["-d", distro, "--"])
    return prefix


def _wsl_shell_command(cfg: dict[str, Any], parts: list[str]) -> list[str]:
    command = " ".join(shlex.quote(part) for part in parts)
    return [*_wsl_prefix(cfg), "bash", "-lc", command]


def load_docker_runtime_config() -> dict[str, Any]:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            merged = dict(DEFAULT_CONFIG)
            merged.update(payload)
            return merged
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def docker_command(*args: str) -> list[str]:
    cfg = load_docker_runtime_config()
    mode = str(cfg.get("mode") or "").lower()
    if mode in {"wsl", "wsl_desktop"}:
        return _wsl_shell_command(cfg, ["docker", *args])
    if mode == "wsl_native":
        socket_path = str(cfg.get("wslSocketPath") or DEFAULT_CONFIG["wslSocketPath"])
        return _wsl_shell_command(cfg, ["env", f"DOCKER_HOST=unix://{socket_path}", "docker", *args])
    return ["docker", *args]


def docker_compose_command(*args: str) -> list[str]:
    cfg = load_docker_runtime_config()
    mode = str(cfg.get("mode") or "").lower()
    if mode in {"wsl", "wsl_desktop"}:
        return _wsl_shell_command(cfg, ["docker", "compose", *args])
    if mode == "wsl_native":
        socket_path = str(cfg.get("wslSocketPath") or DEFAULT_CONFIG["wslSocketPath"])
        return _wsl_shell_command(cfg, ["env", f"DOCKER_HOST=unix://{socket_path}", "docker", "compose", *args])
    return ["docker", "compose", *args]


def is_docker_runtime_command(command: list[str]) -> bool:
    if not command:
        return False
    if command[0] == "docker":
        return True
    if command[0] != "wsl" or "--" not in command:
        return False
    marker = command.index("--")
    if len(command) > marker + 3 and command[marker + 1] == "bash" and command[marker + 2] == "-lc":
        payload = command[marker + 3]
        return "docker " in payload or payload.startswith("docker")
    if len(command) > marker + 1 and command[marker + 1] == "docker":
        return True
    return len(command) > marker + 3 and command[marker + 1] == "env" and command[marker + 3] == "docker"


def describe_docker_runtime() -> str:
    cfg = load_docker_runtime_config()
    mode = str(cfg.get("mode") or "").lower()
    distro = str(cfg.get("wslDistro") or DEFAULT_CONFIG["wslDistro"])
    launcher = "system" if bool(cfg.get("wslUseSystemLauncher", DEFAULT_CONFIG["wslUseSystemLauncher"])) else "user"
    if mode in {"wsl", "wsl_desktop"}:
        return f"wsl:{distro}:{launcher}:desktop-socket"
    if mode == "wsl_native":
        socket_path = str(cfg.get("wslSocketPath") or DEFAULT_CONFIG["wslSocketPath"])
        return f"wsl:{distro}:{launcher}:native-socket:{socket_path}"
    return "windows:docker-cli"
