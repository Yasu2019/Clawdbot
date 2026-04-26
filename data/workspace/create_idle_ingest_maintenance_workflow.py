#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_NAME = "Idle Ingest Maintenance (Every 3h)"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "idle_ingest_maintenance_workflow_status.json"
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def list_workflows() -> list[dict]:
    return request_json("/workflows?limit=100").get("data", [])


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
                "name": "Every 3 Hours",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": "0 */3 * * *"}]
                    }
                },
            },
            {
                "id": "node-run",
                "name": "Run Idle Maintenance",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [260, 0],
                "parameters": {
                    "command": "python3 /workspace/idle_ingest_maintenance.py",
                    "executeOnce": True,
                },
            },
        ],
        "connections": {
            "Every 3 Hours": {
                "main": [[{"node": "Run Idle Maintenance", "type": "main", "index": 0}]]
            }
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
        status["backup"] = backup_workflow(existing, "idle_ingest_maintenance_update")
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
    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
