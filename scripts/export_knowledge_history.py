import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sqlite3
import json
import datetime
import subprocess
from pathlib import Path

DB_FILE = Path("D:/Clawdbot_Docker_20260125/data/workspace/universal_growth.db")
OUTPUT_FILE = Path("D:/Clawdbot_Docker_20260125/data/workspace/apps/growth_dashboard/knowledge_history.json")

def export_knowledge_history():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    
    # 1. Recent (Past 7 days)
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    
    recent_query = """
        SELECT id, timestamp, domain, challenge, source, length(know_how) as know_how_len, difficulty 
        FROM growth_records 
        WHERE timestamp >= ? 
        ORDER BY timestamp DESC
    """
    recent_rows = conn.execute(recent_query, (seven_days_ago,)).fetchall()
    
    recent_list = []
    for r in recent_rows:
        recent_list.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "domain": r["domain"],
            "title": r["challenge"][:100] + ('...' if len(r["challenge"]) > 100 else ''),
            "source": r["source"],
            "score": r["know_how_len"] or 0
        })
        
    # 2. Top 10 Useful (Highest know_how_len + difficulty)
    top10_query = """
        SELECT id, timestamp, domain, challenge, source, length(know_how) as know_how_len, difficulty 
        FROM growth_records 
        WHERE know_how IS NOT NULL
        ORDER BY (COALESCE(difficulty, 1) * length(know_how)) DESC
        LIMIT 10
    """
    top10_rows = conn.execute(top10_query).fetchall()
    
    top10_list = []
    for r in top10_rows:
        top10_list.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "domain": r["domain"],
            "title": r["challenge"][:100] + ('...' if len(r["challenge"]) > 100 else ''),
            "source": r["source"],
            "score": r["know_how_len"] or 0
        })
        
    # 3. Unprocessed Count (Gemini Analysis Queue)
    processed = conn.execute("SELECT external_id FROM ai_summaries_tracking").fetchall()
    processed_ids = set(str(r[0]) for r in processed if r[0])
    
    all_rows = conn.execute("SELECT id, external_id FROM public_api_acquisitions WHERE status = 'downloaded' AND local_path IS NOT NULL AND local_path != ''").fetchall()
    unprocessed_count = 0
    for row in all_rows:
        if str(row[0]) not in processed_ids and str(row[1] or '') not in processed_ids:
            unprocessed_count += 1
            
    output_data = {
        "recent_count": len(recent_list),
        "recent": recent_list,
        "top10": top10_list,
        "unprocessed_count": unprocessed_count,
        "generated_at": datetime.datetime.now().isoformat()
    }
    
    conn.close()
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    youtube_export = Path(__file__).with_name("export_iatf_dashboard.py")
    if youtube_export.exists():
        subprocess.run([sys.executable, str(youtube_export)], check=False)
        
    print(f"Exported {len(recent_list)} recent records and {len(top10_list)} top records to {OUTPUT_FILE}")

if __name__ == "__main__":
    export_knowledge_history()
