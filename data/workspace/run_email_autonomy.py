import time
import os
import glob
import psycopg2
import requests
import json
from datetime import datetime

# Configuration
WATCH_DIR = "/home/node/paperless/consume/email" # Inside Container Path
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "mysecretpassword", # Replace with env var in production
    "host": "postgres",
    "port": 5432
}
OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:32b"

def log(msg):
    print(f"[{datetime.now()}] {msg}")

def connect_db():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def analyze_email(content):
    prompt = f"""
    You are an Email Analyst. Extract the following from this email:
    1. Action Items (Requests from A to B)
    2. Quality Issues (QIF/PIF)
    3. Meeting Minutes/Decisions

    Email Content:
    {content}

    Output JSON format ONLY:
    {{
        "action_items": [{{"requester": "", "assignee": "", "content": "", "due_date": "YYYY-MM-DD"}}],
        "quality_issues": [{{"issuer": "", "type": "QIF/PIF", "details": "", "due_date": ""}}],
        "meetings": [{{"organizer": "", "topic": "", "decisions": ""}}]
    }}
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        return json.loads(response.json()['response'])
    except Exception as e:
        log(f"LLM Error: {e}")
        return None

def process_file(filepath):
    log(f"Processing: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = analyze_email(content)
    if not data:
        return

    conn = connect_db()
    cur = conn.cursor()

    # Insert Action Items
    for item in data.get('action_items', []):
        cur.execute(
            "INSERT INTO action_items (requester_name, assignee_name, content, due_date) VALUES (%s, %s, %s, %s)",
            (item['requester'], item['assignee'], item['content'], item['due_date'] or None)
        )
    
    # Insert Quality Issues
    for item in data.get('quality_issues', []):
        cur.execute(
            "INSERT INTO quality_issues (issuer_name, issue_type, details, due_date) VALUES (%s, %s, %s, %s)",
            (item['issuer'], item['type'], item['details'], item['due_date'] or None)
        )

    # Insert Meetings
    for item in data.get('meetings', []):
        cur.execute(
            "INSERT INTO meeting_records (organizer, topic, decisions) VALUES (%s, %s, %s)",
            (item['organizer'], item['topic'], item['decisions'])
        )

    conn.commit()
    cur.close()
    conn.close()
    log("Data inserted into DB.")

def main():
    log("Clawdbot Email Autonomy Started.")
    # Ensure DB tables exist (Quick check/create could be here, but assuming schema.sql ran)
    
    processed_files = set()
    
    while True:
        files = glob.glob(os.path.join(WATCH_DIR, "*"))
        for f in files:
            if f not in processed_files:
                try:
                    process_file(f)
                    processed_files.add(f)
                    # Move to processed folder? Or let Paperless consume it?
                    # For now, just mark processed in memory.
                except Exception as e:
                    log(f"Error processing {f}: {e}")
        
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    main()
