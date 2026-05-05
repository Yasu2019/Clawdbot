import requests
import json
import os

N8N_URL = "http://localhost:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
HEADERS = {"X-N8N-API-KEY": API_KEY}

def main():
    try:
        r = requests.get(f"{N8N_URL}/workflows", headers=HEADERS)
        r.raise_for_status()
        workflows = r.json().get("data", [])
        
        found = False
        for wf in workflows:
            # We need to get full workflow detail to see nodes
            wf_id = wf["id"]
            rd = requests.get(f"{N8N_URL}/workflows/{wf_id}", headers=HEADERS)
            detail = rd.json().get("data", {})
            nodes = detail.get("nodes", [])
            
            if any(n.get("type") == "n8n-nodes-base.telegramTrigger" for n in nodes):
                print(f"ID: {wf_id} | Name: {detail.get('name')}")
                found = True
        
        if not found:
            print("No Telegram Trigger workflows found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
