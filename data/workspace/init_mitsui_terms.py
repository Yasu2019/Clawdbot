import sqlite3
import os
from pathlib import Path

DB_FILE = Path(r"d:\Clawdbot_Docker_20260125\data\workspace\mitsui_terms.db")
TXT_FILE = Path(r"d:\Clawdbot_Docker_20260125\ミツイ専門用語リスト_20260126.txt")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mitsui_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE,
            category TEXT,
            description TEXT,
            source TEXT,
            detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.close()

def import_from_txt():
    if not TXT_FILE.exists():
        print(f"File not found: {TXT_FILE}")
        return

    try:
        # Try reading as CP932 (Shift-JIS)
        content = TXT_FILE.read_text(encoding="cp932")
    except UnicodeDecodeError:
        content = TXT_FILE.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_FILE)
    current_category = "General"
    
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        
        # Check if it's a category (ends with : or looks like a header)
        if ":" in line and not "," in line:
            current_category = line.split(":")[0].strip()
            continue
        
        # Process terms separated by commas
        terms = [t.strip() for t in line.split(",")]
        for term in terms:
            if not term: continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO mitsui_terms (term, category, source) VALUES (?, ?, ?)",
                    (term, current_category, "Initial Import (Text File)")
                )
            except Exception as e:
                print(f"Error inserting {term}: {e}")
    
    conn.commit()
    conn.close()
    print("Import complete.")

if __name__ == "__main__":
    init_db()
    import_from_txt()
