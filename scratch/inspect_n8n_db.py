
import sqlite3
import os

db_path = r"d:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite"

if not os.path.exists(db_path):
    print(f"DB not found: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT email, id FROM user_entity;")
    rows = cursor.fetchall()
    print("Users in n8n DB:")
    for row in rows:
        print(f"Email: {row[0]}, ID: {row[1]}")
    
    cursor.execute("SELECT name, value FROM auth_user;")
    # Wait, check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables:")
    for t in tables:
        print(t[0])
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
