#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_NAME = "Daily Trend Opportunity Report (20:30 JST)"
TELEGRAM_BOT_TOKEN = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "trend_opportunity_workflow_status.json"
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_workflows() -> list[dict]:
    result = request_json("/workflows?limit=100")
    return result.get("data", [])


def find_workflow_by_name(name: str) -> dict | None:
    for item in list_workflows():
        if item.get("name") == name:
            return request_json(f"/workflows/{item['id']}")
    return None


def backup_workflow(wf: dict, suffix: str) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"workflow_{wf['id']}_{suffix}_{ts}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def build_workflow() -> dict:
    return {
        "name": WORKFLOW_NAME,
        "settings": {"timezone": "Asia/Tokyo", "executionOrder": "v1"},
        "nodes": [
            {
                "id": "node-schedule",
                "name": "Daily 20:30 JST",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "parameters": {
                    "rule": {
                        "interval": [
                            {
                                "field": "cronExpression",
                                "expression": "30 20 * * *",
                            }
                        ]
                    }
                },
            },
            {
                "id": "node-fetch",
                "name": "Fetch Trend Report",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [240, 0],
                "parameters": {
                    "command": "python3 /workspace/fetch_trend_opportunity_report.py",
                },
            },
            {
                "id": "node-format",
                "name": "Format Trend Report",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [500, 0],
                "parameters": {
                    "jsCode": """
const raw = ($input.first().json.stdout || '').trim();
let parsed = {};
try {
  parsed = raw ? JSON.parse(raw) : {};
} catch (error) {
  parsed = { message: 'トレンド日報のJSON解析に失敗しました。\\n\\n' + raw };
}
const msg = String(parsed.message || 'トレンド日報の本文が空です。');
const truncated = msg.length > 3800 ? msg.slice(0, 3800) + '\\n...(省略)' : msg;
return [{ json: { text: truncated } }];
""".strip()
                },
            },
            {
                "id": "node-telegram",
                "name": "Telegram Notify",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [760, 0],
                "parameters": {
                    "method": "POST",
                    "url": f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "chat_id", "value": TELEGRAM_CHAT_ID},
                            {"name": "text", "value": "={{ $json.text }}"},
                        ]
                    },
                    "options": {},
                },
            },
        ],
        "connections": {
            "Daily 20:30 JST": {
                "main": [[{"node": "Fetch Trend Report", "type": "main", "index": 0}]]
            },
            "Fetch Trend Report": {
                "main": [[{"node": "Format Trend Report", "type": "main", "index": 0}]]
            },
            "Format Trend Report": {
                "main": [[{"node": "Telegram Notify", "type": "main", "index": 0}]]
            },
        },
    }


def create_workflow(workflow: dict) -> dict:
    return request_json("/workflows", method="POST", payload=workflow)


def update_workflow(workflow_id: str, workflow: dict) -> dict:
    payload = {k: v for k, v in workflow.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{workflow_id}", method="PUT", payload=payload)


def set_active(workflow_id: str, active: bool) -> dict:
    path = f"/workflows/{workflow_id}/activate" if active else f"/workflows/{workflow_id}/deactivate"
    return request_json(path, method="POST", payload={})


def main() -> None:
    status = {"startedAt": now_jst(), "step": "prepare", "workflowName": WORKFLOW_NAME}
    write_status(status)

    desired = build_workflow()
    existing = find_workflow_by_name(WORKFLOW_NAME)

    if existing:
        status["mode"] = "update"
        status["workflowId"] = existing["id"]
        status["backup"] = backup_workflow(existing, "trend_opportunity_update")
        updated = update_workflow(existing["id"], desired)
        status["updatedAt"] = updated.get("updatedAt")
        workflow_id = existing["id"]
    else:
        status["mode"] = "create"
        created = create_workflow(desired)
        status["createdAt"] = created.get("createdAt")
        status["workflowId"] = created["id"]
        workflow_id = created["id"]

    active_res = set_active(workflow_id, True)
    status["active"] = active_res.get("active", True)
    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
