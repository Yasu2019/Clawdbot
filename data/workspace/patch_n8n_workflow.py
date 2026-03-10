import sqlite3
import json
import os

DB_PATH = '/root/.n8n/database.sqlite'
WORKFLOW_ID = 'sYuks4F4aDvENqpl'

def update_node():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH, timeout=60000)
    cursor = conn.cursor()
    
    cursor.execute('SELECT nodes FROM workflow_entity WHERE id = ?', (WORKFLOW_ID,))
    row = cursor.fetchone()
    if not row:
        print(f"Error: Workflow {WORKFLOW_ID} not found")
        conn.close()
        return

    nodes = json.loads(row[0])
    updated = False
    for n in nodes:
        if n['name'] == 'メッセージ整形':
            n['parameters']['jsCode'] = """
const now = new Date().toLocaleString("ja-JP", {timeZone:"Asia/Tokyo"});
const report = ($input.first() && $input.first().json && ($input.first().json.stdout || $input.first().json.data)) || "(データが空です)";
const truncated = report.length > 3800 ? report.substring(0, 3800) + "\\n...(省略)" : report;
const msg = "📧 P016 Email報告 (" + now + ")\\n\\n" + truncated;
return [{ json: { text: msg } }];
            """.strip()
            updated = True
            break
    
    if updated:
        cursor.execute('UPDATE workflow_entity SET nodes = ? WHERE id = ?', (json.dumps(nodes), WORKFLOW_ID))
        conn.commit()
        print("Successfully updated workflow nodes.")
    else:
        print("Node 'メッセージ整形' not found.")
    
    conn.close()

if __name__ == "__main__":
    update_node()
