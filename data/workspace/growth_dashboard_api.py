from flask import Flask, jsonify
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)
DB_FILE = Path(__file__).resolve().parent / "universal_growth.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/growth-history')
def growth_history():
    if not DB_FILE.exists():
        return jsonify([])
    
    conn = get_db()
    # Count solved challenges per day
    rows = conn.execute("""
        SELECT date(timestamp) as day, COUNT(*) as count 
        FROM growth_records 
        GROUP BY day 
        ORDER BY day ASC
    """).fetchall()
    
    data = [{"day": r["day"], "count": r["count"]} for r in rows]
    conn.close()
    return jsonify(data)

@app.route('/api/domain-stats')
def domain_stats():
    if not DB_FILE.exists():
        return jsonify({})
    
    conn = get_db()
    rows = conn.execute("SELECT domain, COUNT(*) as count FROM growth_records GROUP BY domain").fetchall()
    data = {r["domain"]: r["count"] for r in rows}
    conn.close()
    return jsonify(data)

if __name__ == "__main__":
    # Start on port 18097 to avoid conflicts
    app.run(host='0.0.0.0', port=18097)
