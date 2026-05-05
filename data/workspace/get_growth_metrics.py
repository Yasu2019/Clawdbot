#!/usr/bin/env python3
import sqlite3
import json
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "universal_growth.db"

def get_metrics():
    if not DB_FILE.exists():
        return {"status": "error", "message": "DB not found"}
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        # Total counts per domain
        rows = conn.execute("SELECT domain, COUNT(*) as count FROM growth_records GROUP BY domain").fetchall()
        domain_counts = {row["domain"]: row["count"] for row in rows}
        
        # Latest entries
        latest = conn.execute("SELECT domain, challenge, timestamp FROM growth_records ORDER BY timestamp DESC LIMIT 3").fetchall()
        latest_activities = [{"domain": r["domain"], "challenge": r["challenge"], "ts": r["timestamp"]} for r in latest]
        
        return {
            "status": "success",
            "total_solved": sum(domain_counts.values()),
            "domain_counts": domain_counts,
            "latest_activities": latest_activities
        }
    finally:
        conn.close()

if __name__ == "__main__":
    print(json.dumps(get_metrics(), ensure_ascii=False, indent=2))
