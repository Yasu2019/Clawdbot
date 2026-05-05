import sqlite3
import os
import libsql_client
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE = Path(r"d:\Clawdbot_Docker_20260125\data\workspace")
load_dotenv(WORKSPACE.parents[1] / ".env")
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def backfill():
    local_db = WORKSPACE / "universal_growth.db"
    conn = sqlite3.connect(local_db)
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT domain, challenge, status, know_how, artifact_path, timestamp FROM growth_records").fetchall()
    conn.close()
    
    print(f"Found {len(records)} local records to sync.")
    
    client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
    client.execute("""
        CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            domain TEXT,
            challenge TEXT,
            status TEXT,
            know_how TEXT,
            artifact_path TEXT
        )
    """)
    
    # Check what's already there to avoid duplicates
    existing = client.execute("SELECT timestamp, challenge FROM growth_records").rows
    existing_keys = {(r[0], r[1]) for r in existing}
    
    count = 0
    for r in records:
        if (r['timestamp'], r['challenge']) not in existing_keys:
            client.execute(
                "INSERT INTO growth_records (domain, challenge, status, know_how, artifact_path, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (r['domain'], r['challenge'], r['status'], r['know_how'], r['artifact_path'], r['timestamp'])
            )
            count += 1
    
    client.close()
    print(f"Successfully synced {count} new records to Turso.")

if __name__ == "__main__":
    backfill()
