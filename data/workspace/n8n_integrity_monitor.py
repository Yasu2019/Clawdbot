#!/usr/bin/env python3
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Config
DB_PATH = Path("/home/node/clawd/../clawstack_v2/data/n8n/database.sqlite")
# Note: From gateway container, the host path D:/Clawdbot_Docker_20260125/ is NOT directly accessible.
# But n8n volume is mapped to ./clawstack_v2/data/n8n.
# We should use the path relative to the gateway's workspace if possible, or just use n8n API.

# Better: Use n8n API like workflow_healer.py
N8N_BASE = "http://n8n:5678/rest"
N8N_EMAIL = "y.suzuki.hk@gmail.com"
N8N_PASSWORD = "Foxconnjpn75"
MANIFEST_PATH = Path("/home/node/clawd/n8n_manifest.json")
TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CID = "8173025084"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def get_n8n_token():
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{N8N_BASE}/login",
            data=json.dumps({"emailOrLdapLoginId": N8N_EMAIL, "password": N8N_PASSWORD}).encode(),
            headers={"Content-Type": "application/json", "browser-id": "integrity-mon"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            for hdr in r.headers.get_all("Set-Cookie") or []:
                if "n8n-auth=" in hdr:
                    return hdr.split("n8n-auth=")[1].split(";")[0]
    except Exception as e:
        log(f"Login failed: {e}")
    return ""

def check_integrity():
    if not MANIFEST_PATH.exists():
        log("Manifest not found.")
        return

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    token = get_n8n_token()
    if not token:
        log("Could not get token.")
        return

    import urllib.request
    req = urllib.request.Request(
        f"{N8N_BASE}/workflows?limit=100",
        headers={"Cookie": f"n8n-auth={token}", "browser-id": "integrity-mon"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.load(r)
            # Normalize response
            data = resp.get("data", [])
            if isinstance(data, dict):
                current_workflows = data.get("results", [])
            else:
                current_workflows = data
    except Exception as e:
        log(f"Fetch workflows failed: {e}")
        return

    current_ids = {wf["id"] for wf in current_workflows}
    missing = []
    
    for wf in manifest["critical_workflows"]:
        if wf["id"] not in current_ids:
            missing.append(wf)

    if missing:
        msg = "🚨 <b>[n8n 整合性アラート]</b>\n以下の重要ワークフローが消失しています：\n\n"
        for m in missing:
            msg += f"・{m['name']} (ID: {m['id']})\n"
        msg += "\n自動復旧を試みるか、バックアップからインポートしてください。"
        send_telegram(msg)
        log(f"Alert sent for missing: {[m['name'] for m in missing]}")
    else:
        log("All critical workflows are present.")

def send_telegram(text):
    import urllib.request
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = {"chat_id": TELEGRAM_CID, "text": text, "parse_mode": "HTML"}
    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            pass
    except Exception as e:
        log(f"Telegram failed: {e}")

if __name__ == "__main__":
    check_integrity()
