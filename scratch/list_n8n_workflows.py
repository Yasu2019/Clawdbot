import sqlite3

db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, active FROM workflow_entity")
    rows = cursor.fetchall()
    
    print(f"{'ID':<20} | {'Name':<50} | {'Active'}")
    print("-" * 80)
    for row in rows:
        print(f"{str(row[0]):<20} | {row[1]:<50} | {row[2]}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
