import http.server
import socketserver
import json
import subprocess
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# --- Configuration ---
PORT = 18099  # MuseScore API Port
MUSESCORE_PATH = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
WORKSPACE = Path(r"d:\Clawdbot_Docker_20260125\data\workspace")
TEMP_DIR = WORKSPACE / "apps" / "harmony_hub" / "temp_audio"

os.makedirs(TEMP_DIR, exist_ok=True)

class MuseScoreHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/render':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            
            xml_data = params.get('xml')
            filename = params.get('filename', 'output.wav')
            
            if not xml_data:
                self.send_error(400, "Missing XML data")
                return

            xml_path = TEMP_DIR / "input.xml"
            audio_path = TEMP_DIR / filename
            
            # Save XML
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(xml_data)
            
            # Run MuseScore
            try:
                cmd = [MUSESCORE_PATH, "-o", str(audio_path), str(xml_path)]
                subprocess.run(cmd, check=True, timeout=60)
                
                # Success
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                relative_url = f"temp_audio/{filename}"
                self.wfile.write(json.dumps({
                    "status": "success",
                    "url": relative_url,
                    "full_path": str(audio_path)
                }).encode())
                
            except Exception as e:
                self.send_error(500, str(e))

def run_server():
    with socketserver.TCPServer(("", PORT), MuseScoreHandler) as httpd:
        print(f"MuseScore API Server running at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
