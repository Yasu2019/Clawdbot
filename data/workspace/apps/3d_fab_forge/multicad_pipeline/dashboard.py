import sqlite3
import os
import json
import datetime
import libsql_client
from dotenv import load_dotenv

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "03_logs")

# Load .env from root
load_dotenv(os.path.join(BASE_DIR, "..", "..", "..", "..", "..", ".env"))

DB_FILE = os.path.join(BASE_DIR, "self_training.db")
HTML_FILE = os.path.join(BASE_DIR, "dashboard.html")
HEARTBEAT_FILE = os.path.join(LOG_DIR, "cad_growth_heartbeat.json")

# Turso Config
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def generate_dashboard():
    if not os.path.exists(DB_FILE):
        print("DB not found. Run the daemon first.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM training_logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    # Watchdog Status check
    hb_file = os.path.join(BASE_DIR, "03_logs", "cad_growth_heartbeat.json")
    watchdog_status = "UNKNOWN"
    last_hb_str = "N/A"
    if os.path.exists(hb_file):
        try:
            with open(hb_file, "r", encoding="utf-8") as f:
                hb_data = json.load(f)
                last_hb = datetime.datetime.fromisoformat(hb_data["last_heartbeat"])
                last_hb_str = last_hb.strftime("%Y-%m-%d %H:%M:%S")
                if datetime.datetime.now() - last_hb < datetime.timedelta(minutes=10):
                    watchdog_status = "HEALTHY"
                else:
                    watchdog_status = "STALE"
        except:
            watchdog_status = "ERROR"

    # Turso Cloud check
    cloud_count = 0
    cloud_status = "OFFLINE"
    if TURSO_URL and TURSO_TOKEN:
        try:
            client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
            res = client.execute("SELECT COUNT(*) as count FROM training_logs")
            cloud_count = res.rows[0][0]
            cloud_status = "CONNECTED"
            client.close()
        except Exception as e:
            cloud_status = f"SYNC_ERROR"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>AI Self-Training Dashboard - MultiCAD</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background-color: #0f172a; color: #f8fafc; }}
            .glass {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-6xl mx-auto">
            <header class="mb-12 flex justify-between items-end">
                <div>
                    <h1 class="text-4xl font-800 tracking-tighter mb-2">AI <span class="text-blue-400">Self-Training</span> Dashboard</h1>
                    <p class="text-slate-400">深夜帯の自律訓練・試行錯誤・成長記録</p>
                </div>
                <div class="text-right flex flex-col gap-3">
                    <div class="flex items-center justify-end gap-4">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full {'bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.6)]' if cloud_status == 'CONNECTED' else 'bg-slate-600'}"></span>
                            <span class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Cloud Sync: {cloud_count} records</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full {'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' if watchdog_status == 'HEALTHY' else 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'}"></span>
                            <span class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Watchdog: {watchdog_status}</span>
                        </div>
                    </div>
                    <p class="text-[10px] text-slate-500 mt-1">Last Heartbeat: {last_hb_str}</p>
                </div>
            </header>

            <div class="grid grid-cols-1 gap-6">
                {"".join([f'''
                <div class="glass p-6 rounded-2xl border-l-4 {'border-green-500' if log['status'] == 'SUCCESS' else 'border-rose-500'}">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <span class="text-xs font-bold uppercase tracking-widest text-slate-500">{log['timestamp']}</span>
                            <h3 class="text-xl font-bold mt-1">{log['challenge']}</h3>
                        </div>
                        <span class="px-3 py-1 rounded-full text-xs font-bold {'bg-green-500/20 text-green-400' if log['status'] == 'SUCCESS' else 'bg-rose-500/20 text-rose-400'}">
                            {log['status']}
                        </span>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div class="bg-slate-900/50 p-4 rounded-xl border border-slate-700">
                            <h4 class="text-slate-500 font-bold mb-2 uppercase text-xs">Engine & Result</h4>
                            <p><span class="text-blue-400">Engine:</span> {log['engine']}</p>
                            <p class="mt-2 text-rose-400">{'Error: ' + log['error_message'] if log['error_message'] else 'No errors encountered.'}</p>
                        </div>
                        <div class="bg-slate-900/50 p-4 rounded-xl border border-slate-700">
                            <h4 class="text-slate-500 font-bold mb-2 uppercase text-xs">Measures & Insights</h4>
                            <p>{log['countermeasure']}</p>
                            <p class="mt-2"><span class="text-green-400">Artifact:</span> {os.path.basename(log['artifact_path']) if log['artifact_path'] else 'None'}</p>
                        </div>
                    </div>
                </div>
                ''' for log in logs])}
            </div>

            <footer class="mt-12 text-center text-slate-500 text-sm">
                &copy; 2026 Clawstack MultiCAD Pipeline | Last Updated: {logs[0]['timestamp'] if logs else 'N/A'}
            </footer>
        </div>
    </body>
    </html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard updated: {HTML_FILE}")

if __name__ == "__main__":
    generate_dashboard()
