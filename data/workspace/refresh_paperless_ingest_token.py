#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
CONFIG_PATH = WORKSPACE / "paperless_ingest_config.json"
STATUS_PATH = WORKSPACE / "paperless_token_refresh_status.json"
PAPERLESS_CONTAINER = "clawstack-unified-paperless-1"
DEFAULT_HOST_URL = "http://127.0.0.1:8000"
DEFAULT_GATEWAY_URL = "http://host.docker.internal:8000"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run(command: list[str], timeout_seconds: int = 60) -> dict[str, Any]:
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


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def inspect_paperless_env() -> dict[str, str]:
    result = run(["docker", "inspect", PAPERLESS_CONTAINER, "--format", "{{json .Config.Env}}"], 30)
    if result.get("returncode") != 0:
        raise RuntimeError(result.get("stderr") or "failed to inspect paperless container")
    raw = json.loads(result.get("stdout") or "[]")
    env: dict[str, str] = {}
    for item in raw:
        if "=" not in str(item):
            continue
        key, value = str(item).split("=", 1)
        env[key] = value
    return env


def fetch_token(host_url: str, username: str, password: str) -> str:
    resp = requests.post(
        f"{host_url.rstrip('/')}/api/token/",
        json={"username": username, "password": password},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    token = str(payload.get("token") or "").strip()
    if not token:
        raise RuntimeError("Paperless token response did not include token")
    return token


def main() -> None:
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "stage": "starting",
    }
    write_json(STATUS_PATH, status)

    env = inspect_paperless_env()
    username = str(env.get("PAPERLESS_ADMIN_USER") or "admin").strip()
    password = str(env.get("PAPERLESS_ADMIN_PASSWORD") or "admin").strip()
    host_url = DEFAULT_HOST_URL
    gateway_url = DEFAULT_GATEWAY_URL
    token = fetch_token(host_url, username, password)

    current = read_json(CONFIG_PATH, {})
    current.update(
        {
            "paperlessUrl": gateway_url,
            "paperlessToken": token,
            "paperlessHostUrl": host_url,
            "updatedAt": now_jst_text(),
            "updatedBy": "refresh_paperless_ingest_token.py",
        }
    )
    write_json(CONFIG_PATH, current)

    status.update(
        {
            "updatedAt": now_jst_text(),
            "stage": "completed",
            "paperlessHostUrl": host_url,
            "paperlessGatewayUrl": gateway_url,
            "username": username,
            "tokenPreview": f"{token[:8]}...{token[-6:]}",
        }
    )
    write_json(STATUS_PATH, status)
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
