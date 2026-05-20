#!/usr/bin/env python3
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parents[1]
STATUS_PATH = WORKSPACE / "p009_self_growth_watchdog_status.json"
STATE_DIR = ROOT / "data" / "state" / "p009_self_growth_watchdog"
HARNESS_PATH = STATE_DIR / "harness_status.json"

API_COST_STATUS = WORKSPACE / "api_cost_report_status.json"
SELF_GROWTH_STATUS = WORKSPACE / "agent_self_growth_memory_hygiene_status.json"
SELF_GROWTH_HARNESS = ROOT / "data" / "state" / "agent_self_growth_memory_hygiene" / "harness_status.json"
PDCA_STATUS = WORKSPACE / "pdca_lab" / "state" / "status.json"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ["%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"]:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=JST) if raw.endswith("JST") else datetime.strptime(raw, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def age_minutes(payload: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        dt = parse_dt(payload.get(key))
        if dt:
            return round((now_jst().astimezone(dt.tzinfo) - dt).total_seconds() / 60.0, 1)
    return None


def run_command(command: list[str], timeout_seconds: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_seconds)
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }
    except Exception as exc:
        return {"command": " ".join(command), "returncode": 1, "stderr_tail": str(exc), "timedOut": False}


def ps_contains(token: str) -> bool:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*{token}*' }} | Select-Object -First 1 ProcessId | ConvertTo-Json -Compress",
    ]
    result = run_command(cmd, 20)
    return "ProcessId" in str(result.get("stdout_tail") or "")


def diagnose() -> dict[str, Any]:
    p009_age = age_minutes(read_json(API_COST_STATUS), ["generated_at_jst", "updatedAt", "startedAt"])
    self_growth_age = age_minutes(read_json(SELF_GROWTH_STATUS), ["updatedAt", "startedAt"])
    self_growth_harness_age = age_minutes(read_json(SELF_GROWTH_HARNESS), ["updatedAt"])
    pdca_age = age_minutes(read_json(PDCA_STATUS), ["updatedAt", "created_at", "startedAt"])
    return {
        "p009_age_minutes": p009_age,
        "self_growth_age_minutes": self_growth_age,
        "self_growth_harness_age_minutes": self_growth_harness_age,
        "self_growth_process": ps_contains("agent_self_growth_memory_hygiene.py"),
        "pdca_age_minutes": pdca_age,
    }


def run_cycle() -> dict[str, Any]:
    before = diagnose()
    actions: dict[str, Any] = {}

    auto_repair_cmd = ["python", str(WORKSPACE / "auto_repair_allowed.py")]
    actions["auto_repair_allowed"] = run_command(auto_repair_cmd, 900)

    after = diagnose()
    payload = {
        "service": "p009_self_growth_watchdog",
        "updatedAt": now_text(),
        "stage": "healthy" if actions["auto_repair_allowed"].get("returncode") == 0 else "degraded",
        "before": before,
        "actions": actions,
        "after": after,
    }
    write_json(STATUS_PATH, payload)
    write_json(HARNESS_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep P009, PDCA refresh, and self-growth hygiene from going stale.")
    parser.add_argument("--poll-seconds", type=int, default=1800)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        run_cycle()
        if args.once:
            return 0
        time.sleep(max(args.poll_seconds, 300))


if __name__ == "__main__":
    raise SystemExit(main())
