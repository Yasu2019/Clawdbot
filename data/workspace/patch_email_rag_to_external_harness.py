#!/usr/bin/env python3
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


JST = timezone(timedelta(hours=9))
API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_ID = "0qNc6FdnxdDFICGe"

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "patch_email_rag_to_external_harness_status.json"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    response = requests.request(method, f"{API_BASE}{path}", headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def backup_workflow(wf: dict, suffix: str) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"workflow_{wf['id']}_{suffix}_{ts}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def main() -> None:
    status = {"startedAt": now_jst(), "step": "fetch"}
    write_status(status)

    wf = request_json(f"/workflows/{WORKFLOW_ID}")
    status["backup"] = backup_workflow(wf, "pre_external_harness_patch")
    write_status(status)

    wf["nodes"] = [
        {
            "id": "node-schedule",
            "name": "Daily 02:00 JST",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 0],
            "parameters": {
                "rule": {
                    "interval": [
                        {
                            "field": "cronExpression",
                            "expression": "0 2 * * *",
                        }
                    ]
                }
            },
        },
        {
            "id": "node-run",
            "name": "run_email_rag_harness",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [260, 0],
            "parameters": {
                "executeOnce": True,
                "command": "python3 /workspace/run_email_rag_ingest_report.py",
            },
        },
    ]
    wf["connections"] = {
        "Daily 02:00 JST": {
            "main": [[{"node": "run_email_rag_harness", "type": "main", "index": 0}]]
        }
    }
    wf["settings"] = {
        "timezone": "Asia/Tokyo",
        "executionOrder": "v1",
        "callerPolicy": "workflowsFromSameOwner",
        "availableInMCP": False,
    }
    wf["staticData"] = {"node:Daily 02:00 JST": {"recurrenceRules": []}}

    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf["settings"],
        "staticData": wf["staticData"],
    }

    status["step"] = "update"
    write_status(status)
    updated = request_json(f"/workflows/{WORKFLOW_ID}", method="PUT", payload=payload)
    status["updatedAt"] = updated.get("updatedAt")
    status["newSettings"] = updated.get("settings")
    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
