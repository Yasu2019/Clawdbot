
import json
import os
import time
import sys
from datetime import datetime

STATUS_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\ingest_status.json"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_status():
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def draw_progress_bar(percent, width=30):
    hashes = int(percent / 100 * width)
    spaces = width - hashes
    return "[" + "#" * hashes + "." * spaces + "]"

def main():
    print("Starting Ingestion Monitor...")
    time.sleep(1)
    
    try:
        while True:
            now = datetime.now()
            clear_screen()
            print(f"=== Tolerance Analysis Knowledge Ingestion Dashboard ===")
            print(f"Current Time:  {now.strftime('%H:%M:%S')}")
            print(f"Status:        ACTIVE (Refreshing every 2s)")
            print("-" * 75)
            print(f"{'Task Name':<25} | {'Progress':<32} | {'Updated'} | {'Details'}")
            print("-" * 75)
            
            data = get_status()
            
            if not data:
                print("Waiting for status data from background processes...")
            else:
                for task, info in data.items():
                    current = info.get("current", 0)
                    total = info.get("total", 0)
                    percent = info.get("progress_percent", 0)
                    msg = info.get("message", "")
                    ts_str = info.get("timestamp", "")
                    
                    # Calculate seconds ago
                    time_ago = "Unknown"
                    if ts_str:
                        try:
                            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            diff = (now - ts).total_seconds()
                            if diff < 60:
                                time_ago = f"{int(diff)}s ago"
                            else:
                                time_ago = f"{int(diff//60)}m ago"
                        except:
                            pass

                    bar = draw_progress_bar(percent)
                    progress_str = f"{bar} {percent:>5.1f}%"
                    
                    # Truncate message if too long
                    if len(msg) > 25:
                        msg = msg[:22] + "..."
                        
                    print(f"{task:<25} | {progress_str} | {time_ago:<7} | {msg}")
            
            print("-" * 75)
            print("Press Ctrl+C to exit monitor (Ingestion continues in background)")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitor exited.")

if __name__ == "__main__":
    main()
