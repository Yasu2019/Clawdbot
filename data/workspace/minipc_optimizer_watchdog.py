#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "minipc_optimizer_watchdog_status.json"
STATE_PATH = WORKSPACE / "minipc_optimizer_watchdog_state.json"
HARNESS_PATH = ROOT / "data" / "state" / "minipc_optimizer_watchdog" / "harness_status.json"
OPTIMIZER_SCRIPT = WORKSPACE / "minipc_optimizer.py"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def run_command(command: list[str], timeout_seconds: int = 120) -> dict[str, Any]:
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


def memory_snapshot() -> dict[str, Any]:
    ps_script = (
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "$total = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2); "
        "$free = [math]::Round($os.FreePhysicalMemory / 1MB, 2); "
        "$used = [math]::Round($total - $free, 2); "
        "$freePct = if ($total -gt 0) { [math]::Round(($free / $total) * 100, 1) } else { 0 }; "
        "@{ totalGb = $total; freeGb = $free; usedGb = $used; freePercent = $freePct } | ConvertTo-Json -Compress"
    )
    result = run_command(["powershell", "-NoProfile", "-Command", ps_script], 30)
    if result.get("returncode") != 0 or not result.get("stdout"):
        return {"ok": False, "probe": result}
    try:
        payload = json.loads(result["stdout"])
    except Exception:
        return {"ok": False, "probe": result}
    payload["ok"] = True
    return payload


def read_optimizer_status() -> dict[str, Any]:
    return load_json(WORKSPACE / "minipc_optimizer_status.json", {})


def run_optimizer(command_name: str) -> dict[str, Any]:
    return run_command(["python", str(OPTIMIZER_SCRIPT), command_name], 1200)


def should_apply_lite(memory: dict[str, Any], optimizer_status: dict[str, Any], args: argparse.Namespace) -> tuple[bool, str]:
    if not memory.get("ok"):
        return False, "memory probe unavailable"
    free_gb = float(memory.get("freeGb") or 0.0)
    free_pct = float(memory.get("freePercent") or 0.0)
    heavy = optimizer_status.get("heavyRunningCandidates") or []
    if not heavy:
        return False, "no heavy running candidates"
    if free_gb <= args.free_gb_threshold:
        return True, f"free memory {free_gb}GB <= threshold {args.free_gb_threshold}GB"
    if free_pct <= args.free_percent_threshold:
        return True, f"free memory percent {free_pct}% <= threshold {args.free_percent_threshold}%"
    return False, "memory headroom is sufficient"


def write_status(status: dict[str, Any]) -> None:
    save_json(STATUS_PATH, status)
    save_json(
        HARNESS_PATH,
        {
            "service": "minipc_optimizer_watchdog",
            "updatedAt": now_jst().isoformat(),
            "pid": os.getpid(),
            "state": status.get("stage"),
            "lastAction": status.get("lastAction"),
            "reason": status.get("reason"),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatically apply mini PC lite mode when memory pressure is high")
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--free-gb-threshold", type=float, default=10.0)
    parser.add_argument("--free-percent-threshold", type=float, default=20.0)
    parser.add_argument("--cooldown-minutes", type=int, default=180)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = load_json(STATE_PATH, {})
    cycle = int(state.get("cycle", 0))

    while True:
        cycle += 1
        status: dict[str, Any] = {
            "startedAt": state.get("startedAt") or now_jst_text(),
            "updatedAt": now_jst_text(),
            "cycle": cycle,
            "pid": os.getpid(),
            "stage": "evaluating",
            "lastAction": "none",
            "reason": "",
        }
        memory = memory_snapshot()
        status["memory"] = memory

        status_result = run_optimizer("status")
        optimizer_status = read_optimizer_status()
        status["optimizerStatusResult"] = status_result
        status["optimizerStatus"] = {
            "capturedAt": optimizer_status.get("capturedAt"),
            "heavyRunningCandidates": optimizer_status.get("heavyRunningCandidates") or [],
        }

        should_apply, reason = should_apply_lite(memory, optimizer_status, args)
        status["reason"] = reason

        last_apply_at = parse_dt(str((state.get("lastApply") or {}).get("at") or ""))
        cooldown_active = bool(
            last_apply_at
            and (now_jst().astimezone(last_apply_at.tzinfo) - last_apply_at) < timedelta(minutes=args.cooldown_minutes)
        )
        if should_apply and not cooldown_active:
            status["stage"] = "applying_lite_mode"
            status["lastAction"] = "apply_lite"
            write_status(status)
            apply_result = run_optimizer("apply-lite")
            status["applyResult"] = apply_result
            status["stage"] = "completed"
            state["lastApply"] = {
                "at": now_jst_text(),
                "reason": reason,
                "result": apply_result,
            }
        elif should_apply:
            status["stage"] = "cooldown"
            status["lastAction"] = "cooldown_skip"
            status["cooldownUntil"] = (
                last_apply_at + timedelta(minutes=args.cooldown_minutes)
            ).strftime("%Y-%m-%d %H:%M:%S JST") if last_apply_at else None
        else:
            status["stage"] = "healthy"

        status["updatedAt"] = now_jst_text()
        write_status(status)
        state["cycle"] = cycle
        state["startedAt"] = status["startedAt"]
        save_json(STATE_PATH, state)

        if args.once:
            return
        time.sleep(max(args.poll_seconds, 60))


if __name__ == "__main__":
    main()
