import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(r'd:\Clawdbot_Docker_20260125')
REVIEW_SCRIPT = REPO_ROOT / 'clawstack_v2' / 'openclaw_qa_engineering_studios' / 'scripts' / 'run_review.py'
STATUS_FILE = REPO_ROOT / 'data' / 'workspace' / 'central_patrol_status.json'

POLL_INTERVAL = 14400 # 4 hours

def update_status(stage, last_run=None, error=None):
    status = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"),
        "stage": stage,
        "lastRun": last_run,
        "error": error,
        "frequency": "Every 4 hours (High)"
    }
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        import json
        json.dump(status, f, indent=2, ensure_ascii=False)

def run_patrol():
    print(f"[{datetime.now()}] Starting Central Patrol...")
    update_status("running")
    try:
        # Run the full QA review
        result = subprocess.run(['python', str(REVIEW_SCRIPT), '--mode', 'full'], 
                              capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print("Patrol completed successfully.")
            update_status("healthy", last_run=datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"))
        else:
            print(f"Patrol failed with exit code {result.returncode}")
            update_status("failed", error=result.stderr)
    except Exception as e:
        print(f"Patrol exception: {str(e)}")
        update_status("error", error=str(e))

def main():
    print("Central Patrol Watchdog started (Frequency: High).")
    while True:
        run_patrol()
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
