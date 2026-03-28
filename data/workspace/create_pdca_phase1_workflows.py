#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "pdca_phase1_workflows_status.json"
JST = timezone(timedelta(hours=9))

WORKFLOWS = [
    {
        "name": "pdca_capture_ingest",
        "cron": "15 */6 * * *",
        "command": "python3 /workspace/pdca_feedback_phase1.py refresh",
        "description": "Phase 1 capture refresh and status rollup",
    },
    {
        "name": "pdca_auto_score",
        "cron": "45 */6 * * *",
        "command": "python3 /workspace/pdca_feedback_phase1.py refresh",
        "description": "Phase 1 scoring refresh placeholder",
    },
    {
        "name": "pdca_collect_feedback",
        "cron": "0 8 * * *",
        "command": "python3 /workspace/pdca_feedback_phase1.py refresh",
        "description": "Phase 1 feedback queue refresh placeholder",
    },
]


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def list_workflows() -> list[dict]:
    return request_json("/workflows?limit=200").get("data", [])


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


def build_workflow(name: str, cron_expr: str, command: str, description: str) -> dict:
    return {
        "name": name,
        "settings": {"timezone": "Asia/Tokyo", "executionOrder": "v1"},
        "nodes": [
            {
                "id": "schedule",
                "name": "Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "cronExpression", "expression": cron_expr}]
                    }
                },
            },
            {
                "id": "run",
                "name": "Run PDCA Harness",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [300, 0],
                "parameters": {"command": command, "executeOnce": True},
            },
        ],
        "connections": {"Schedule": {"main": [[{"node": "Run PDCA Harness", "type": "main", "index": 0}]]}},
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
    status = {"startedAt": now_jst(), "step": "prepare", "results": []}
    write_status(status)
    for spec in WORKFLOWS:
        row = {"name": spec["name"], "cron": spec["cron"], "command": spec["command"], "description": spec["description"]}
        try:
            desired = build_workflow(spec["name"], spec["cron"], spec["command"], spec["description"])
            existing = find_workflow_by_name(spec["name"])
            if existing:
                row["mode"] = "update"
                row["workflowId"] = existing["id"]
                row["backup"] = backup_workflow(existing, spec["name"])
                update_workflow(existing["id"], desired)
                set_active(existing["id"], True)
            else:
                row["mode"] = "create"
                created = create_workflow(desired)
                row["workflowId"] = created["id"]
                set_active(created["id"], True)
            row["ok"] = True
        except Exception as exc:
            row["ok"] = False
            row["error"] = str(exc)
        status["results"].append(row)
        write_status(status)
    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
