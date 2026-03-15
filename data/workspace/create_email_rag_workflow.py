#!/usr/bin/env python3
"""
Create n8n workflow: "Email RAG Ingest (Nightly)"
Runs daily at 02:00 JST (17:00 UTC):
  1. Phase 1+2: ingest_eml_v2.py (body + attachments → Qdrant)
  2. Phase 3:   ingest_eml_to_meili.py (keyword → Meilisearch)
  3. Telegram notification on completion
"""
import json, requests

N8N_URL = "http://localhost:5679"
N8N_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
TG_TOKEN = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
GATEWAY  = "clawstack-unified-clawdbot-gateway-1"

headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}

workflow = {
    "name": "Email RAG Ingest (Nightly 02:00 JST)",
    "nodes": [
        {
            "id": "trigger",
            "name": "nightly_trigger",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 0],
            "parameters": {
                "rule": {"interval": [{"field": "cronExpression", "expression": "0 17 * * *"}]}
            }
        },
        {
            "id": "phase12",
            "name": "phase12_qdrant",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [250, 0],
            "parameters": {
                "executeOnce": True,
                "command": f"docker exec {GATEWAY} sh -lc \"python3 /home/node/clawd/ingest_eml_v2.py >>/home/node/clawd/ingest_eml.log 2>&1; tail -5 /home/node/clawd/ingest_eml.log\" || true"
            }
        },
        {
            "id": "phase3",
            "name": "phase3_meilisearch",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [500, 0],
            "parameters": {
                "executeOnce": True,
                "command": f"docker exec {GATEWAY} sh -lc \"python3 /home/node/clawd/ingest_eml_to_meili.py >>/home/node/clawd/ingest_eml.log 2>&1; tail -3 /home/node/clawd/ingest_eml.log\" || true"
            }
        },
        {
            "id": "notify",
            "name": "telegram_notify",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [750, 0],
            "parameters": {
                "method": "POST",
                "url": f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                "sendBody": True,
                "contentType": "json",
                "body": {
                    "chat_id": "{{ $json.chat_id ?? '7769164479' }}",
                    "text": "=📧 *Email RAG Ingest 完了*\n\n🔵 Qdrant: {{ $node[\"phase12_qdrant\"].json.stdout.split('\\n').slice(-3).join('\\n') }}\n🟢 Meilisearch: {{ $node[\"phase3_meilisearch\"].json.stdout.split('\\n').slice(-2).join('\\n') }}",
                    "parse_mode": "Markdown"
                },
                "options": {}
            }
        }
    ],
    "connections": {
        "nightly_trigger": {"main": [[{"node": "phase12_qdrant", "type": "main", "index": 0}]]},
        "phase12_qdrant":  {"main": [[{"node": "phase3_meilisearch", "type": "main", "index": 0}]]},
        "phase3_meilisearch": {"main": [[{"node": "telegram_notify", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"},
    "staticData": None
}

# Check if workflow already exists
r = requests.get(f"{N8N_URL}/api/v1/workflows?limit=50", headers=headers)
existing = {w["name"]: w["id"] for w in r.json().get("data", [])}

if "Email RAG Ingest (Nightly 02:00 JST)" in existing:
    wid = existing["Email RAG Ingest (Nightly 02:00 JST)"]
    r = requests.put(f"{N8N_URL}/api/v1/workflows/{wid}", headers=headers, json={
        "name": workflow["name"], "nodes": workflow["nodes"],
        "connections": workflow["connections"], "settings": workflow["settings"],
        "staticData": None
    })
    print(f"Updated workflow {wid}: {r.status_code}")
else:
    r = requests.post(f"{N8N_URL}/api/v1/workflows", headers=headers, json=workflow)
    print(f"Created workflow: {r.status_code}")
    if r.ok:
        wid = r.json().get("id")
        # Activate
        r2 = requests.patch(f"{N8N_URL}/api/v1/workflows/{wid}", headers=headers,
                            json={"active": True})
        print(f"Activated: {r2.status_code} | id={wid}")

print("Done.")
