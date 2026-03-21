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
STATUS_PATH = ROOT / "data" / "workspace" / "fix_email_rag_trigger_status.json"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    response = requests.request(
        method,
        f"{API_BASE}{path}",
        headers=headers,
        json=payload,
        timeout=30,
    )
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
    status["name"] = wf["name"]
    status["backup"] = backup_workflow(wf, "pre_email_rag_trigger_fix")
    status["originalSettings"] = copy.deepcopy(wf.get("settings") or {})
    write_status(status)

    wf["settings"] = copy.deepcopy(wf.get("settings") or {})
    wf["settings"]["timezone"] = "Asia/Tokyo"
    wf["settings"]["executionOrder"] = wf["settings"].get("executionOrder", "v1")
    wf["settings"]["callerPolicy"] = wf["settings"].get("callerPolicy", "workflowsFromSameOwner")
    wf["settings"]["availableInMCP"] = False

    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf["settings"],
        "staticData": wf.get("staticData") or {},
    }

    status["step"] = "update"
    write_status(status)
    updated = request_json(f"/workflows/{WORKFLOW_ID}", method="PUT", payload=payload)

    status["step"] = "completed"
    status["updatedAt"] = updated.get("updatedAt")
    status["newSettings"] = updated.get("settings")
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
