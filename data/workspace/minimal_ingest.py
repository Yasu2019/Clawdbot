import os
import sqlite3
import json
import glob
import requests
from email import message_from_file

DB_FILE = "/workspace/email_analysis.db"
EMAIL_DIR = "/local_emails"
OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT UNIQUE, 
        email_date TEXT, sender TEXT, request_item TEXT, deadline TEXT, 
        response TEXT, importance TEXT, is_resolved INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()

def main():
    init_db()
    print("Scanning for EML files...")
    files = glob.glob(os.path.join(EMAIL_DIR, "**/*.eml"), recursive=True)
    files = sorted(files, key=os.path.getmtime, reverse=True)[:5] # Just 5 newest
    print(f"Processing {len(files)} newest files...")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    for f in files:
        print(f"Analyzing {os.path.basename(f)}...")
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                msg = message_from_file(fp)
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                         p = part.get_payload(decode=True)
                         if p: body += p.decode('utf-8', errors='ignore')
            else:
                p = msg.get_payload(decode=True)
                if p: body = p.decode('utf-8', errors='ignore')

            prompt = f"Analyze this email and extract JSON: {body[:2000]}"
            resp = requests.post(OLLAMA_URL, 
                                 json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False, 'format': 'json', 'options': {'num_ctx': 1024}}, 
                                 timeout=300)
            analysis = json.loads(resp.json()['response'])
            
            c.execute("INSERT OR REPLACE INTO analyses (filepath, email_date, sender, request_item, deadline, response, importance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (f, msg.get('date'), msg.get('from'), str(analysis.get('依頼事項','-')), str(analysis.get('納期','-')), str(analysis.get('回答','-')), str(analysis.get('重要度','-'))))
            conn.commit()
            print("  ✅ Saved.")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
