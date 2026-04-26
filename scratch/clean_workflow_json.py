import json
import os

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
        
        # Remove shared and id to let n8n assign new ones
        if 'shared' in data:
            del data['shared']
        if 'id' in data:
            # We might want to keep the ID if it's referenced elsewhere, 
            # but for restoration to a new DB, it's safer to let n8n assign it.
            # However, the user might expect the same ID.
            # Let's try removing it first.
            del data['id']
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Cleaned {file_path}")
    except Exception as e:
        print(f"Failed to clean {file_path}: {e}")
