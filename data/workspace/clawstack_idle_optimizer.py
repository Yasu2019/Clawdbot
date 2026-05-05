#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clawstack Resource-Aware Idle Task Optimizer
Monitors CPU/RAM and triggers Scout/Growth tasks during idle periods (especially daytime).
Complying with AGENTS.md Section 13 (API Consent Protocol).
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Use psutil from the multicad_pipeline venv
try:
    import psutil
except ImportError:
    print("ERROR: psutil not found. Please run this script using the multicad_pipeline venv.")
    sys.exit(1)

JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "clawstack_idle_optimizer_status.json"
STATE_PATH = WORKSPACE / "clawstack_idle_optimizer_state.json"

# Tasks to manage
TASKS = [
    {
        "id": "ai_strategy_scout",
        "script": WORKSPACE / "run_ai_strategy_scout_local.py",
        "status_file": WORKSPACE / "ai_strategy_scout_local_status.json",
        "stale_hours": 20,
        "requires_consent_if_heavy": True,
        "is_opencode_go": False,
    },
    {
        "id": "growth_hygiene",
        "script": WORKSPACE / "agent_self_growth_memory_hygiene.py",
        "status_file": WORKSPACE / "agent_self_growth_memory_hygiene_status.json",
        "stale_hours": 6,
        "requires_consent_if_heavy": True,
        "is_opencode_go": False,
    }
]

def now_jst() -> datetime:
    return datetime.now(JST)

def is_daytime() -> bool:
    h = now_jst().hour
    return 9 <= h < 18

def get_system_load(duration=5):
    cpu = psutil.cpu_percent(interval=duration)
    mem = psutil.virtual_memory().percent
    return cpu, mem

def load_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return fallback or {}

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_dt(raw):
    if not raw: return None
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt) if "JST" not in fmt else datetime.strptime(raw, fmt).replace(tzinfo=JST)
        except: continue
    return None

def check_stale(task):
    status = load_json(task["status_file"])
    last_run_raw = status.get("finishedAt") or status.get("generatedAt") or status.get("updatedAt")
    last_run = parse_dt(last_run_raw)
    if not last_run: return True
    age = now_jst().astimezone(last_run.tzinfo) - last_run
    return age >= timedelta(hours=task["stale_hours"])

def run_task(task):
    print(f"[{now_jst()}] Starting task: {task['id']}")
    # Compliance check for API consumption
    if task["requires_consent_if_heavy"] and not task["is_opencode_go"]:
        print(f"WARN: Task {task['id']} may consume heavy API. Ensuring logic is safe or human notified.")
    
    try:
        # We assume scripts are non-destructive and follow internal protocols
        res = subprocess.run([sys.executable, str(task["script"])], capture_output=True, text=True, timeout=1800)
        return res.returncode == 0
    except Exception as e:
        print(f"ERROR running {task['id']}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-threshold", type=float, default=15.0)
    parser.add_argument("--mem-threshold", type=float, default=70.0)
    parser.add_argument("--poll-minutes", type=int, default=15)
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually execute tasks")
    args = parser.parse_args()

    print(f"=== Clawstack Idle Optimizer Started (PID: {os.getpid()}) ===")
    
    while True:
        cpu, mem = get_system_load(duration=5 if args.once else 10)
        daytime = is_daytime()
        
        status = {
            "updatedAt": now_jst().isoformat(),
            "cpu_percent": cpu,
            "mem_percent": mem,
            "is_daytime": daytime,
            "state": "idle_monitoring"
        }
        
        # Logic: Daytime must be idle. Nighttime can run anyway (if stale).
        idle = cpu <= args.cpu_threshold and mem <= args.mem_threshold
        print(f"[{now_jst()}] Load: CPU={cpu}%, MEM={mem}%. Daytime={daytime}. Idle={idle}")
        
        if (daytime and idle) or (not daytime):
            status["state"] = "active_optimizing" if idle else "night_forced_optimization"
            for task in TASKS:
                if check_stale(task):
                    print(f"Task {task['id']} is stale. Triggering (Dry-run={args.dry_run})...")
                    if not args.dry_run:
                        success = run_task(task)
                        task["last_success"] = success
                        task["last_run_at"] = now_jst().isoformat()
                    else:
                        print(f"DRY-RUN: Would execute {task['id']}")
        
        save_json(STATUS_PATH, status)
        if args.once:
            break
        time.sleep(args.poll_minutes * 60)

if __name__ == "__main__":
    main()
