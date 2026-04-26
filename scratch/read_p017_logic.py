import sqlite3
import json

db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nodes FROM workflow_entity WHERE name LIKE '%P017%'")
    row = cursor.fetchone()
    if row:
        nodes = json.loads(row[0])
        print(json.dumps(nodes, indent=2, ensure_ascii=False))
    else:
        print("P017 not found in DB.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
