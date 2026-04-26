import sqlite3
import json
import uuid
import datetime
import argparse
from pathlib import Path

def import_workflow(file_path, wf_id=None, project_id='FSQkUb1XFWSTzJW3'):
    db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not wf_id:
            # Generate a random n8n-style ID if not provided (usually 16 chars)
            wf_id = str(uuid.uuid4()).replace('-', '')[:16]
            
        # Check if workflow already exists
        cursor.execute("SELECT id FROM workflow_entity WHERE id = ?", (wf_id,))
        if cursor.fetchone():
            print(f"Workflow {wf_id} already exists, skipping.")
            return wf_id

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
            data.get('name', 'Imported Workflow'),
            1 if data.get('active', True) else 0,
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
        
        # Link to project
        cursor.execute("""
            INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?)
        """, (wf_id, project_id, 'workflow:owner', now, now))
        
        conn.commit()
        conn.close()
        print(f"Successfully imported workflow '{data.get('name')}' as {wf_id}")
        return wf_id
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--id", default=None)
    parser.add_argument("--project", default='FSQkUb1XFWSTzJW3')
    args = parser.parse_args()
    import_workflow(args.file, args.id, args.project)
