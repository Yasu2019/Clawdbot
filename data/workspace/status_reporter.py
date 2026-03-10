
import json
import os
import time
from datetime import datetime

STATUS_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\ingest_status.json"

def update_status(task_name, current, total, message="Running"):
    """
    Updates the status of a task in the shared JSON file.
    """
    data = {}
    
    # Read existing data if possible
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}
    
    # Update current task
    progress = 0
    if total > 0:
        progress = (current / total) * 100
        
    data[task_name] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current": current,
        "total": total,
        "progress_percent": round(progress, 1),
        "message": message,
        "status": "Running" if current < total else "Completed"
    }
    
    # Write back
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to update status: {e}")

def mark_complete(task_name):
    update_status(task_name, 0, 0, message="Completed") # Handled by logic above usually, but explicit helper

