import os
import json
import socket
import platform
import subprocess
import ctypes
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# RAM取得のためのctypes構造体
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_cpu_usage():
    try:
        # wmic is deprecated/removed in newer Windows 11. Use Get-CimInstance via PowerShell.
        # CREATE_NO_WINDOW (0x08000000) を指定して裏側でのフリーズを完全に防ぐ
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average"],
            text=True,
            creationflags=0x08000000,
            timeout=5
        )
        val = out.strip()
        if val.isdigit() or val.replace('.', '', 1).isdigit():
            return float(val)
    except:
        pass
    return 0.0

def get_ram_info():
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        
        total_gb = stat.ullTotalPhys / (1024**3)
        free_gb = stat.ullAvailPhys / (1024**3)
        used_gb = total_gb - free_gb
        percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0
        return round(used_gb, 2), round(total_gb, 2), round(percent, 1)
    except:
        pass
    return 0.0, 0.0, 0.0

def get_cpu_temp():
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance -Namespace 'root\\wmi' -Class MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"],
            text=True,
            creationflags=0x08000000,
            timeout=3
        )
        lines = out.strip().split('\n')
        temps = []
        for line in lines:
            val = line.strip()
            if val.isdigit():
                celsius = (float(val) / 10.0) - 273.15
                temps.append(celsius)
        if temps:
            return round(max(temps), 1)
    except:
        pass
    return None

# サーマルスロットリング用変数
THROTTLE_HIGH_C = 85.0
THROTTLE_LOW_C = 70.0
THROTTLE_PERCENT = 60
NORMAL_PERCENT = 100

is_throttling = False

def set_cpu_limit(percent):
    try:
        # 電源プランを切り替えるのではなく、現在のプランの「CPU最大状態」を直接書き換えて確実に制限をかける
        subprocess.check_output(["powercfg", "-setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(percent)], text=True, creationflags=0x08000000, timeout=3)
        subprocess.check_output(["powercfg", "-setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(percent)], text=True, creationflags=0x08000000, timeout=3)
        subprocess.check_output(["powercfg", "-setactive", "SCHEME_CURRENT"], text=True, creationflags=0x08000000, timeout=3)
    except:
        pass

def thermal_watchdog_loop():
    global is_throttling
    while True:
        temp = get_cpu_temp()
        if temp is not None:
            if temp >= THROTTLE_HIGH_C and not is_throttling:
                print(f"[{datetime.now()}] Thermal Throttling ON: {temp}C (Limiting CPU to {THROTTLE_PERCENT}%)")
                set_cpu_limit(THROTTLE_PERCENT)
                is_throttling = True
            elif temp <= THROTTLE_LOW_C and is_throttling:
                set_cpu_limit(NORMAL_PERCENT)
                print(f"[{datetime.now()}] Thermal Throttling OFF: {temp}C (Restoring CPU to {NORMAL_PERCENT}%)")
                is_throttling = False
        time.sleep(15)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == "/metrics":
            used_gb, total_gb, ram_percent = get_ram_info()
            data = {
                "hostname": socket.gethostname(),
                "os": platform.system(),
                "cpu_usage_percent": get_cpu_usage(),
                "ram_usage_percent": ram_percent,
                "ram_used_gb": used_gb,
                "ram_total_gb": total_gb,
                "cpu_temp_celsius": get_cpu_temp(),
                "is_throttling": is_throttling
            }
            
            response = json.dumps(data).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path == "/download_db":
            db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="universal_growth.db"')
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                with open(db_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Database file not found.")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/upload_harvest":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                # Setup inbox directory
                inbox_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\knowledge_ingestion\inbox"
                os.makedirs(inbox_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"harvest_{socket.gethostname()}_{int(time.time())}.txt"
                file_path = os.path.join(inbox_dir, filename)
                
                # Save the harvested data
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(post_data)
                
                # Update Dashboard JSON
                try:
                    title = "Unknown Title"
                    keyword = "UNKNOWN"
                    content = ""
                    for line in post_data.split('\n'):
                        if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip()
                        elif line.startswith("KEYWORD:"): keyword = line.replace("KEYWORD:", "").strip()
                    
                    content_idx = post_data.find("CONTENT:")
                    if content_idx != -1:
                        content = post_data[content_idx+8:].strip()
                        
                    # Handle full transcripts separately
                    is_transcript = False
                    is_email = False
                    email_subject = ""
                    for line in post_data.split('\n'):
                        if line.startswith("TYPE:") and "YOUTUBE_TRANSCRIPT" in line:
                            is_transcript = True
                        elif line.startswith("TYPE:") and "INTERNAL_EMAIL" in line:
                            is_email = True
                        elif line.startswith("SUBJECT:"):
                            email_subject = line.replace("SUBJECT:", "").strip()
                    
                    if is_transcript:
                        transcript_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\transcripts"
                        os.makedirs(transcript_dir, exist_ok=True)
                        ts_file = os.path.join(transcript_dir, f"transcript_{socket.gethostname()}_{int(time.time())}.txt")
                        with open(ts_file, 'w', encoding='utf-8') as f:
                            f.write(post_data)
                        print(f"[{datetime.now()}] Received full transcript, saved to {ts_file}")
                        # Skip adding full transcripts to dashboard to avoid clutter
                    elif is_email:
                        stats_path = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\growth_dashboard\growth_stats.json"
                        if os.path.exists(stats_path):
                            with open(stats_path, 'r', encoding='utf-8') as sf:
                                stats = json.load(sf)
                                
                            new_entry = {
                                "domain": "INTERNAL_KNOWHOW",
                                "challenge": f"【Becky!過去メール】{email_subject}",
                                "know_how": content[:120] + "...",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if "recent_know_how" not in stats:
                                stats["recent_know_how"] = []
                            stats["recent_know_how"].insert(0, new_entry)
                            stats["recent_know_how"] = stats["recent_know_how"][:20]
                            
                            if "domain_stats" not in stats:
                                stats["domain_stats"] = {}
                            stats["domain_stats"]["INTERNAL_KNOWHOW"] = stats["domain_stats"].get("INTERNAL_KNOWHOW", 0) + 1
                            
                            try:
                                import sqlite3
                                db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
                                conn = sqlite3.connect(db_path)
                                conn.row_factory = sqlite3.Row
                                rows = conn.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM growth_records WHERE timestamp >= date('now', '-30 days', 'localtime') GROUP BY day ORDER BY day ASC").fetchall()
                                stats["history"] = [{"day": r["day"], "count": r["count"]} for r in rows]
                                conn.close()
                            except Exception as e:
                                print(f"Error syncing history: {e}")

                            stats["updated_at"] = datetime.now().isoformat()
                            with open(stats_path, 'w', encoding='utf-8') as sf:
                                json.dump(stats, sf, indent=2, ensure_ascii=False)
                        print(f"[{datetime.now()}] Received internal email: {email_subject}")
                    else:
                        stats_path = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\growth_dashboard\growth_stats.json"
                        if os.path.exists(stats_path):
                            with open(stats_path, 'r', encoding='utf-8') as sf:
                                stats = json.load(sf)
                                
                            # Format for dashboard
                            # Format for dashboard
                            domain_key = "IATF" if "IATF" in keyword else ("CAE_MATERIAL" if "Mold" in keyword else "GENERAL")
                            new_entry = {
                                "domain": domain_key,
                                "challenge": f"【Dynabook自動収集】{title}",
                                "know_how": content[:120] + "...",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if "recent_know_how" not in stats:
                                stats["recent_know_how"] = []
                            stats["recent_know_how"].insert(0, new_entry)
                            stats["recent_know_how"] = stats["recent_know_how"][:20] # keep latest 20
                            
                            if "domain_stats" not in stats:
                                stats["domain_stats"] = {}
                            stats["domain_stats"][domain_key] = stats["domain_stats"].get(domain_key, 0) + 1
                            
                            try:
                                import sqlite3
                                db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
                                conn = sqlite3.connect(db_path)
                                conn.row_factory = sqlite3.Row
                                rows = conn.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM growth_records WHERE timestamp >= date('now', '-30 days', 'localtime') GROUP BY day ORDER BY day ASC").fetchall()
                                stats["history"] = [{"day": r["day"], "count": r["count"]} for r in rows]
                                conn.close()
                            except Exception as e:
                                print(f"Error syncing history: {e}")

                            stats["updated_at"] = datetime.now().isoformat()
                            
                            with open(stats_path, 'w', encoding='utf-8') as sf:
                                json.dump(stats, sf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Failed to update dashboard JSON: {e}")

                print(f"[{datetime.now()}] Received and saved harvest data to {filename}")
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Harvest data received successfully.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Empty payload.")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run(server_class=HTTPServer, handler_class=MetricsHandler, port=8111):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    
    # Start thermal watchdog
    watchdog_thread = threading.Thread(target=thermal_watchdog_loop, daemon=True)
    watchdog_thread.start()
    
    print(f"Starting Fast Monitor Agent on {socket.gethostname()}:{port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
