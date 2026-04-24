#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Constants
JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
CONFIG_PATH = WORKSPACE / "file_server_sync_config.json"
STATUS_PATH = WORKSPACE / "file_server_sync_status.json"

def now_jst_text():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: Config not found at {CONFIG_PATH}")
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing config: {e}")
        return None

def write_status(payload):
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def run_sync(pair, exclusions, dry_run=False):
    source = pair["source"]
    destination = pair["destination"]
    
    # Base command: robocopy "source" "destination"
    # /MIR: Mirror directory tree
    # /R:3 /W:5: 3 retries, 5 sec wait
    # /NP: No Progress
    # /L: List only (Dry Run)
    cmd = ["robocopy", source, destination, "/MIR", "/R:3", "/W:5", "/NP"]
    
    # Add exclusions
    if exclusions:
        cmd.append("/XF")
        cmd.extend(exclusions)
    
    if dry_run:
        cmd.append("/L")
    
    print(f"--- Syncing: {pair['name']} ---")
    print(f"Source: {source}")
    print(f"Dest:   {destination}")
    
    try:
        # Robocopy return codes:
        # 0: No files copied, no changes.
        # 1: Successful copy.
        # 2-7: Various successful states.
        # >=8: Errors occurred.
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="cp932", errors="replace")
        
        return {
            "name": pair["name"],
            "returncode": result.returncode,
            "success": result.returncode < 8,
            "stdout": result.stdout[-2000:], # Keep last 2k chars
            "timestamp": now_jst_text()
        }
    except Exception as e:
        return {
            "name": pair["name"],
            "success": False,
            "error": str(e),
            "timestamp": now_jst_text()
        }

def main():
    parser = argparse.ArgumentParser(description="File Server Sync Harness")
    parser.add_argument("--dry-run", action="store_true", help="List changes without copying")
    args = parser.parse_args()
    
    config = load_config()
    if not config:
        return

    status = {
        "last_run": now_jst_text(),
        "dry_run": args.dry_run,
        "results": []
    }
    
    active_pairs = [p for p in config.get("sync_pairs", []) if p.get("active", False)]
    
    if not active_pairs:
        print("No active sync pairs found in config. Please set 'active': true for at least one pair.")
        return

    for pair in active_pairs:
        res = run_sync(pair, config.get("global_exclusions", []), dry_run=args.dry_run)
        status["results"].append(res)
        
    write_status(status)
    print("\nSync completed. Status written to file_server_sync_status.json")

if __name__ == "__main__":
    main()
