import sqlite3

db_path = r'D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n\database.sqlite'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Try different tables where API key might be
    tables = ['user', 'credentials_entity', 'workflow_entity']
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM \"{table}\" LIMIT 1")
            cols = [description[0] for description in cursor.description]
            print(f"Columns in {table}: {cols}")
            
            if 'id' in cols:
                cursor.execute(f"SELECT id, email FROM \"{table}\"")
                print(f"IDs in {table}:", cursor.fetchall())
        except Exception as te:
            print(f"Could not read {table}: {te}")
            
    # Also check projects
    try:
        cursor.execute("SELECT id, name FROM project")
        print("Projects:", cursor.fetchall())
    except Exception as pe:
        print(f"Could not read project table: {pe}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
