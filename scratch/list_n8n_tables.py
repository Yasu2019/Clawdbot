
import sqlite3
import os

db_path = r"d:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:")
    for t in tables:
        print(t[0])
    conn.close()
except Exception as e:
    print(f"Error: {e}")
