"""Create P017 Workflow Self-Healer in n8n via REST API."""
import json, urllib.request, urllib.error

API = "http://n8n:5678/api/v1"
KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"

def n8n(path, method="GET", data=None):
    headers = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(f"{API}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body[:300]}")

# Delete the test workflow created earlier
try:
    wfs = n8n("/workflows?limit=100")
    for w in wfs.get("data", []):
        if w["name"] in ("P017 Workflow Self-Healer",):
            n8n(f"/workflows/{w['id']}", method="DELETE")
            print(f"Deleted existing: {w['id']} {w['name']}")
except Exception as e:
    print(f"Cleanup: {e}")

TELEGRAM_URL = "https://api.telegram.org/bot8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4/sendMessage"
TELEGRAM_CID = "8173025084"

# JavaScript for the parse node — carefully avoiding literal newlines in strings
parse_js_lines = [
    "const out = ($input.first().json.stdout || '') + ($input.first().json.stderr || '');",
    "const NL = String.fromCharCode(10);",
    "const lines = out.split(NL);",
    "const healerLine = lines.find(function(l){ return l.indexOf('HEALER_MSGS:') === 0; }) || '';",
    "const msgs = healerLine.replace('HEALER_MSGS:', '').trim();",
    "const hasErr = lines.some(function(l){ return l.indexOf('FATAL') >= 0 || l.indexOf('[ERROR]') >= 0; });",
    "return [{ json: { hasAction: msgs.length > 0, summary: msgs || '', hasError: hasErr, raw: out.substring(0, 1000) } }];",
]

workflow = {
    "name": "P017 Workflow Self-Healer",
    "nodes": [
        {
            "id": "n1",
            "name": "15分毎スケジュール",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 300],
            "parameters": {
                "rule": {
                    "interval": [{"field": "minutes", "minutesInterval": 15}]
                }
            }
        },
        {
            "id": "n2",
            "name": "Healer実行",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [280, 300],
            "parameters": {
                "command": "python3 /workspace/workflow_healer.py 2>&1 | tail -80"
            }
        },
        {
            "id": "n3",
            "name": "結果解析",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [560, 300],
            "parameters": {
                "jsCode": "\n".join(parse_js_lines)
            }
        },
        {
            "id": "n4",
            "name": "Telegram通知 (アクション時)",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [840, 160],
            "parameters": {
                "method": "POST",
                "url": TELEGRAM_URL,
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({chat_id: '" + TELEGRAM_CID + "', text: '\\u{1F527} Workflow Healer\\n' + $json.summary, parse_mode: 'HTML'}) }}",
                "options": {}
            }
        },
        {
            "id": "n5",
            "name": "Telegram通知 (エラー時)",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [840, 440],
            "parameters": {
                "method": "POST",
                "url": TELEGRAM_URL,
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({chat_id: '" + TELEGRAM_CID + "', text: '\\u26A0\\uFE0F Healer内部エラー:\\n' + $json.raw.substring(0, 500)}) }}",
                "options": {}
            }
        },
        {
            "id": "n6",
            "name": "アクション判定",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3,
            "position": [680, 300],
            "parameters": {
                "mode": "expression",
                "output": "={{ $json.hasError ? 2 : ($json.hasAction ? 1 : 0) }}"
            }
        }
    ],
    "connections": {
        "15分毎スケジュール": {
            "main": [[{"node": "Healer実行", "type": "main", "index": 0}]]
        },
        "Healer実行": {
            "main": [[{"node": "結果解析", "type": "main", "index": 0}]]
        },
        "結果解析": {
            "main": [[{"node": "アクション判定", "type": "main", "index": 0}]]
        },
        "アクション判定": {
            "main": [
                [],  # output 0: no action → do nothing
                [{"node": "Telegram通知 (アクション時)", "type": "main", "index": 0}],  # output 1
                [{"node": "Telegram通知 (エラー時)", "type": "main", "index": 0}],       # output 2
            ]
        }
    },
    "settings": {"executionOrder": "v1"}
}

result = n8n("/workflows", method="POST", data=workflow)
wf_id = result.get("id")
print(f"Created workflow ID: {wf_id}")

# Activate
act = n8n(f"/workflows/{wf_id}/activate", method="POST")
print(f"Active: {act.get('active')}")
print("P017 Workflow Self-Healer is ready!")
