import json
import os

new_user_id = '6d53a0c1-4e90-4bf7-8d0a-61c6ace6b3cb'
new_project_id = 'FSQkUb1XFWSTzJW3'

files = [
    r'D:\Clawdbot_Docker_20260125\data\workspace\restore\p016.json',
    r'D:\Clawdbot_Docker_20260125\data\workspace\restore\promises.json',
    r'D:\Clawdbot_Docker_20260125\data\workspace\restore\health_check.json',
    r'D:\Clawdbot_Docker_20260125\data\workspace\restore\rag_ingest.json'
]

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # In n8n workflow JSON, the shared info is in a list
        if 'shared' in data:
            for share in data['shared']:
                if 'projectId' in share:
                    share['projectId'] = new_project_id
                if 'userId' in share:
                    share['userId'] = new_user_id
                if 'project' in share:
                    share['project']['id'] = new_project_id
                    share['project']['creatorId'] = new_user_id
                    if 'projectRelations' in share['project']:
                        for rel in share['project']['projectRelations']:
                            rel['userId'] = new_user_id
                            rel['projectId'] = new_project_id
                            if 'user' in rel:
                                rel['user']['id'] = new_user_id
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated {file_path}")
    except Exception as e:
        print(f"Failed to update {file_path}: {e}")
