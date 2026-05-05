import requests
import sqlite3
import re
from pathlib import Path

# --- Configuration ---
WORKSPACE = Path(r"d:\Clawdbot_Docker_20260125\data\workspace")
DB_FILE = WORKSPACE / "mitsui_terms.db"
EMAIL_API_URL = "http://localhost:8792/search" # Assumes existing search API

def extract_terms_from_text(text):
    # Heuristic: Katakana sequences, All-caps English (3+ chars), or terms in brackets
    terms = []
    # Katakana
    terms.extend(re.findall(r'[\u30A1-\u30F6]{2,}', text))
    # All caps (e.g., IATF, FMEA, MOST)
    terms.extend(re.findall(r'[A-Z]{3,}', text))
    # Brackets
    terms.extend(re.findall(r'「(.*?)」', text))
    return list(set(terms))

def process_mitsui_emails():
    # Search for emails from mitsui-s.com
    try:
        # Note: In a real run, this would call the actual Email Search API
        # Here we simulate the query for latest mitsui emails
        params = {"query": "@mitsui-s.com", "limit": 20}
        # res = requests.get(EMAIL_API_URL, params=params)
        # emails = res.json()
        emails = [] # Placeholder
        
        conn = sqlite3.connect(DB_FILE)
        for email in emails:
            content = email.get('body', '')
            found_terms = extract_terms_from_text(content)
            for term in found_terms:
                if len(term) > 20: continue # Skip long sentences
                conn.execute(
                    "INSERT OR IGNORE INTO mitsui_terms (term, category, source) VALUES (?, ?, ?)",
                    (term, "Auto-Detected (Email)", f"Email ID: {email.get('id')}")
                )
        conn.commit()
        conn.close()
        print(f"Processed {len(emails)} emails for terminology extraction.")
    except Exception as e:
        print(f"Error processing emails: {e}")

if __name__ == "__main__":
    process_mitsui_emails()
