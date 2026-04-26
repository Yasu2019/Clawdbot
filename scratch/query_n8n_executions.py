import sqlite3
import json
from datetime import datetime

db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'
workflow_id = 'sYuks4F4aDvENqpl'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query for the last 10 executions of the specific workflow
    query = """
    SELECT id, workflowId, status, startedAt, stoppedAt, waitTill
    FROM execution_entity
    WHERE workflowId = ?
    ORDER BY startedAt DESC
    LIMIT 10
    """
    
    cursor.execute(query, (workflow_id,))
    rows = cursor.fetchall()
    
    print(f"Last 10 executions for P016 ({workflow_id}):")
    print("-" * 80)
    print(f"{'ID':<10} | {'Status':<15} | {'Started At':<25} | {'Stopped At':<25}")
    print("-" * 80)
    
    for row in rows:
        eid, wid, status, started, stopped, wait = row
        print(f"{eid:<10} | {status:<15} | {started:<25} | {stopped:<25}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
