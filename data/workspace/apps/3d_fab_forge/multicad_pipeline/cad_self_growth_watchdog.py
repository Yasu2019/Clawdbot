import os
import json
import time
import subprocess
import datetime
from pathlib import Path

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_PATH = os.path.join(BASE_DIR, "cad_self_growth_daemon.py")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "03_logs", "cad_growth_heartbeat.json")
LOG_FILE = os.path.join(BASE_DIR, "03_logs", "watchdog.log")

def log_event(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def get_daemon_pid():
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("pid")
        except:
            pass
    return None

def is_heartbeat_stale(threshold_minutes=5):
    if not os.path.exists(HEARTBEAT_FILE):
        return True
    
    try:
        with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_hb = datetime.datetime.fromisoformat(data["last_heartbeat"])
            diff = datetime.datetime.now() - last_hb
            return diff > datetime.timedelta(minutes=threshold_minutes)
    except:
        return True

def start_daemon():
    log_event("Starting MultiCAD Self-Growth Daemon...")
    # Run in background without waiting
    subprocess.Popen(["python", DAEMON_PATH], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL, 
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)

def kill_process(pid):
    if not pid: return
    log_event(f"Killing stale process {pid}...")
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
    except Exception as e:
        log_event(f"Failed to kill process: {e}")

def monitor():
    log_event("CAD Self-Growth Watchdog started.")
    while True:
        pid = get_daemon_pid()
        stale = is_heartbeat_stale()
        
        if stale:
            log_event("Heartbeat is stale or missing. Restarting daemon...")
            if pid:
                kill_process(pid)
            start_daemon()
        else:
            # Optionally check if process actually exists
            pass
            
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    monitor()
