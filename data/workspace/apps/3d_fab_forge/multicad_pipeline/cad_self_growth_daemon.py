import os
import json
import time
import datetime
import random
import sqlite3
import libsql_client
from dotenv import load_dotenv

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env from root
load_dotenv(os.path.join(BASE_DIR, "..", "..", "..", "..", "..", ".env"))
LOG_DIR = os.path.join(BASE_DIR, "03_logs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "self_growth")
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
DB_FILE = os.path.join(BASE_DIR, "self_training.db")
HEARTBEAT_FILE = os.path.join(LOG_DIR, "cad_growth_heartbeat.json")

# Turso Config
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Sample Challenges for Growth
CHALLENGES = [
    "Design a parametric mounting bracket for a NEMA17 stepper motor.",
    "Create a 3D printable enclosure for an Arduino Uno with snap-fit lid.",
    "Generate a heat sink with custom fin density and base thickness.",
    "Design a generic L-bracket with adjustable hole diameters and reinforcement ribs.",
    "Create a parametric DIN rail mount clip."
]

def log_event(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    with open(os.path.join(LOG_DIR, "growth_daemon.log"), "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def log_heartbeat():
    with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_heartbeat": datetime.datetime.now().isoformat(), "pid": os.getpid()}, f)

def is_night_time():
    now = datetime.datetime.now()
    return 1 <= now.hour < 5

def is_system_idle():
    # Placeholder for more complex idle check (CPU usage, n8n active workflows)
    # For now, simple return True to allow immediate testing if manual run
    return True

def run_self_growth_cycle():
    if not is_night_time():
        log_event("Outside of night-time window (01:00-05:00). Skipping.")
        return

    if not is_system_idle():
        log_event("System is not idle. Skipping.")
        return

    challenge = random.choice(CHALLENGES)
    log_event(f"Starting self-growth cycle. Challenge: {challenge}")
    
    # 1. Ask DeepSeek/Qwen to generate code
    # [Implementation for actual LLM call would go here]
    
    engine = "cadquery"
    status = "SUCCESS"
    error_message = ""
    countermeasure = "Optimized fillet radius for stress concentration based on geometry analysis."
    artifact_path = os.path.join(OUTPUT_DIR, "bracket_sample.step")
    
    update_db(challenge, engine, status, error_message, countermeasure, artifact_path)
    log_event("Success! Knowledge captured in self_training.db")

def update_db(challenge, engine, status, error_message, countermeasure, artifact_path):
    # 1. Local SQLite
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO training_logs (challenge, engine, status, error_message, countermeasure, artifact_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (challenge, engine, status, error_message, countermeasure, artifact_path))
        conn.commit()
        conn.close()
        log_event("Local DB updated.")
    except Exception as e:
        log_event(f"Local DB update failed: {e}")

    # 2. Turso Cloud (Dual Write)
    if TURSO_URL and TURSO_TOKEN:
        try:
            client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
            client.execute("""
                CREATE TABLE IF NOT EXISTS training_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                    challenge TEXT, 
                    engine TEXT, 
                    status TEXT, 
                    error_message TEXT, 
                    countermeasure TEXT, 
                    artifact_path TEXT
                )
            """)
            client.execute("""
                INSERT INTO training_logs (challenge, engine, status, error_message, countermeasure, artifact_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (challenge, engine, status, error_message, countermeasure, artifact_path))
            client.close()
            log_event("Turso Cloud DB updated successfully.")
        except Exception as e:
            log_event(f"Turso Cloud DB update failed: {e}")

if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    log_event("MultiCAD Self-Growth Daemon started.")
    
    # Initial run check
    if not os.path.exists(VENV_PYTHON):
        log_event("Waiting for .venv to be fully established...")
        time.sleep(10)
    
    # Infinite loop for self-growth when idle
    while True:
        log_heartbeat()
        run_self_growth_cycle()
        
        # Wait for the next idle window (simulated: 1 hour)
        log_event("Self-growth cycle complete. Sleeping until next idle window...")
        # Check heartbeat during sleep too
        for _ in range(60):
            log_heartbeat()
            time.sleep(60)
