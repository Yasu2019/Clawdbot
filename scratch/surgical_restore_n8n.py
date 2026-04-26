import sqlite3
import json
import uuid
import datetime

db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'

files = [
    (r'D:\Clawdbot_Docker_20260125\data\workspace\restore\p016.json', 'sYuks4F4aDvENqpl'),
    (r'D:\Clawdbot_Docker_20260125\data\workspace\restore\promises.json', 'SG2teXHO94CvzCoU'),
    (r'D:\Clawdbot_Docker_20260125\data\workspace\restore\health_check.json', 'vo3Yhdb8M97JQHfx'),
    (r'D:\Clawdbot_Docker_20260125\data\workspace\restore\rag_ingest.json', '0qNc6FdnxdDFICGe')
]

new_project_id = 'FSQkUb1XFWSTzJW3'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for file_path, wf_id in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if workflow already exists
            cursor.execute("SELECT id FROM workflow_entity WHERE id = ?", (wf_id,))
            if cursor.fetchone():
                print(f"Workflow {wf_id} already exists in workflow_entity, skipping insert.")
            else:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                
                # Prepare values
                nodes = json.dumps(data.get('nodes', []))
                connections = json.dumps(data.get('connections', {}))
                settings = json.dumps(data.get('settings', {}))
                staticData = json.dumps(data.get('staticData', {}))
                pinData = json.dumps(data.get('pinData', {}))
                meta = json.dumps(data.get('meta', {}))
                
                cursor.execute("""
                    INSERT INTO workflow_entity (
                        id, name, active, nodes, connections, settings, staticData, 
                        pinData, versionId, triggerCount, meta, createdAt, updatedAt, 
                        isArchived, versionCounter, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wf_id,
                    data.get('name', 'Restored Workflow'),
                    1 if data.get('active') else 0,
                    nodes,
                    connections,
                    settings,
                    staticData,
                    pinData,
                    data.get('versionId', str(uuid.uuid4())),
                    data.get('triggerCount', 0),
                    meta,
                    now,
                    now,
                    0,
                    data.get('versionCounter', 1),
                    data.get('description', '')
                ))
                print(f"Inserted workflow {wf_id} into workflow_entity")

            # Check if shared_workflow link already exists
            cursor.execute("SELECT workflowId FROM shared_workflow WHERE workflowId = ? AND projectId = ?", (wf_id, new_project_id))
            if cursor.fetchone():
                print(f"Workflow {wf_id} already shared with project {new_project_id}, skipping.")
            else:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                cursor.execute("""
                    INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?)
                """, (wf_id, new_project_id, 'workflow:owner', now, now))
                print(f"Linked workflow {wf_id} to project {new_project_id} in shared_workflow")
                
        except Exception as fe:
            print(f"Failed to process {file_path}: {fe}")
            
    conn.commit()
    conn.close()
    print("Done surgical restoration.")
except Exception as e:
    print(f"Error: {e}")
