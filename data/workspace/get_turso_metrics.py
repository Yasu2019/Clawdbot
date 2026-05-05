#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Try to import libsql_client
try:
    import libsql_client
except ImportError:
    # If not in the current environment, we'll suggest using the venv
    print(json.dumps({"error": "libsql_client not found in current environment. Please run with the multicad venv."}))
    sys.exit(1)

from dotenv import load_dotenv

# Locate .env
ROOT_DIR = Path(__file__).resolve().parents[2]
DOTENV_PATH = ROOT_DIR / ".env"

if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if not TURSO_URL or not TURSO_TOKEN:
    print(json.dumps({"error": "TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not found in .env"}))
    sys.exit(1)

def fetch_metrics():
    try:
        client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
        
        # Fetch training_logs count
        rs = client.execute("SELECT COUNT(*) as count FROM training_logs")
        record_count = rs.rows[0][0]
        
        # Optional: Fetch latest timestamp
        rs_latest = client.execute("SELECT MAX(timestamp) FROM training_logs")
        latest_ts = rs_latest.rows[0][0] if rs_latest.rows else None
        
        return {
            "status": "success",
            "record_count": record_count,
            "latest_timestamp": latest_ts,
            "database_url": TURSO_URL
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    metrics = fetch_metrics()
    print(json.dumps(metrics, ensure_ascii=False))
