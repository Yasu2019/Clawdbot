#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_NAME = "Daily Local LLM / OSS Scout (No API)"
ROOT = Path(__file__).absolute().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "local_llm_oss_scout_workflow_status.json"
JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_workflows() -> list[dict]:
    payload = request_json("/workflows")
    return payload.get("data", payload if isinstance(payload, list) else [])


def backup_workflow(wf: dict) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_local_llm_oss_scout_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def desired_workflow() -> dict:
    return {
        "name": WORKFLOW_NAME,
        "settings": {"timezone": "Asia/Tokyo", "executionOrder": "v1"},
        "nodes": [
            {
                "id": "node-schedule",
                "name": "Daily 06:40 JST",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": "40 6 * * *"}]
                    }
                },
            },
            {
                "id": "node-run",
                "name": "Run Local LLM / OSS Scout",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [260, 0],
                "parameters": {
                    "command": "python3 /workspace/fetch_local_llm_oss_digest.py",
                    "executeOnce": True,
                },
            },
        ],
        "connections": {
            "Daily 06:40 JST": {
                "main": [[{"node": "Run Local LLM / OSS Scout", "type": "main", "index": 0}]]
            }
        },
    }


def normalize_for_update(wf: dict) -> dict:
    return {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}


def set_active(workflow_id: str, active: bool) -> dict:
    path = f"/workflows/{workflow_id}/activate" if active else f"/workflows/{workflow_id}/deactivate"
    return request_json(path, method="POST", payload={})


def main() -> int:
    status = {"startedAt": now_jst(), "step": "checking"}
    write_status(status)
    target = desired_workflow()
    existing = next((wf for wf in list_workflows() if wf.get("name") == WORKFLOW_NAME), None)
    if existing:
        full = request_json(f"/workflows/{existing['id']}")
        status["backup"] = backup_workflow(full)
        updated = request_json(f"/workflows/{existing['id']}", method="PUT", payload=target)
        active_res = set_active(existing["id"], True)
        status.update(
            {
                "workflowId": existing["id"],
                "action": "updated",
                "updatedAt": updated.get("updatedAt"),
                "active": active_res.get("active", True),
                "finishedAt": now_jst(),
                "step": "completed",
            }
        )
    else:
        created = request_json("/workflows", method="POST", payload=target)
        active_res = set_active(created["id"], True)
        status.update(
            {
                "workflowId": created.get("id"),
                "action": "created",
                "active": active_res.get("active", True),
                "finishedAt": now_jst(),
                "step": "completed",
            }
        )
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
