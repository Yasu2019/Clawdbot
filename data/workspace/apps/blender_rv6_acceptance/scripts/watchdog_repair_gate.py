#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watchdog + Repair Gate: 最大リトライ数を超えたら自動修復を止めます。"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse, subprocess, time, json
from pathlib import Path
from datetime import datetime

def classify_error(stderr: str) -> str:
    s = stderr.lower()
    if "out of memory" in s or "cuda out of memory" in s: return "memory_or_vram_limit"
    if "permission" in s or "access denied" in s: return "permission_error"
    if "file not found" in s or "no such file" in s: return "missing_file"
    if "timeout" in s: return "timeout"
    if "editorframework" in s or "ue5" in s: return "ue5_headless_known_risk"
    return "unknown"

def run_with_watchdog(command: str, max_repair: int, timeout_sec: int, log_path: Path):
    attempts=[]; last_error_type=None; same_error_count=0
    for attempt in range(max_repair + 1):
        print(f"Attempt {attempt + 1}/{max_repair + 1}: {command}")
        started = datetime.now().isoformat()
        try:
            cp = subprocess.run(command, shell=True, timeout=timeout_sec, text=True, capture_output=True)
            error_type = classify_error(cp.stderr)
            attempts.append({"attempt": attempt+1, "started": started, "returncode": cp.returncode, "error_type": error_type, "stdout_tail": cp.stdout[-2000:], "stderr_tail": cp.stderr[-2000:]})
            if cp.returncode == 0: break
            same_error_count = same_error_count + 1 if error_type == last_error_type else 1
            last_error_type = error_type
            if same_error_count >= 2:
                print("Same error repeated. Stop automatic repair."); break
            time.sleep(2)
        except subprocess.TimeoutExpired as e:
            attempts.append({"attempt": attempt+1, "started": started, "returncode": None, "error_type": "timeout", "stdout_tail": str(e.stdout)[-2000:], "stderr_tail": str(e.stderr)[-2000:]})
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps({"command": command, "max_repair": max_repair, "attempts": attempts, "final_decision": "success" if attempts and attempts[-1]["returncode"] == 0 else "hold_for_human_or_agent_review"}, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--command", required=True); ap.add_argument("--max-repair", type=int, default=2); ap.add_argument("--timeout-sec", type=int, default=1800); ap.add_argument("--log", default="logs/watchdog_repair_log.json")
    a=ap.parse_args(); run_with_watchdog(a.command, a.max_repair, a.timeout_sec, Path(a.log))
if __name__ == "__main__": main()
