#!/usr/bin/env python3
import json
import time
import urllib.request
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKFLOW_ID = "7CpooDw45JT71deJ"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "trend_opportunity_trigger_once_status.json"


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


def backup_workflow(wf: dict, suffix: str) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"workflow_{wf['id']}_{suffix}_{ts}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def schedule_node(wf: dict) -> dict:
    for node in wf["nodes"]:
        if node.get("type") == "n8n-nodes-base.scheduleTrigger":
            return node
    raise RuntimeError("scheduleTrigger not found")


def set_cron(node: dict, cron_expr: str) -> None:
    node["parameters"] = {
        "rule": {
            "interval": [
                {
                    "field": "cronExpression",
                    "expression": cron_expr,
                }
            ]
        }
    }


def update_workflow(wf: dict) -> dict:
    payload = {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{wf['id']}", method="PUT", payload=payload)


def poll_execution(workflow_id: str, started_after_iso: str, timeout_seconds: int = 180) -> dict | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = request_json(f"/executions?workflowId={workflow_id}&limit=10")
        for item in result.get("data", []):
            started_at = item.get("startedAt")
            if started_at and started_at >= started_after_iso:
                if item.get("status") in {"success", "error", "canceled", "crashed"}:
                    return item
        time.sleep(5)
    return None


def main() -> None:
    status = {"startedAt": now_jst(), "workflowId": WORKFLOW_ID, "step": "prepare"}
    write_status(status)

    wf = request_json(f"/workflows/{WORKFLOW_ID}")
    original_wf = copy.deepcopy(wf)
    status["backup"] = backup_workflow(wf, "pre_trigger_once")
    node = schedule_node(wf)
    status["originalSchedule"] = json.loads(json.dumps(node.get("parameters", {}), ensure_ascii=False))

    trigger_time = datetime.now(JST).replace(second=0, microsecond=0) + timedelta(minutes=2)
    cron_expr = f"{trigger_time.minute} {trigger_time.hour} * * *"
    started_after_iso = datetime.now(timezone.utc).isoformat()

    set_cron(node, cron_expr)
    updated = update_workflow(wf)
    status["temporaryCron"] = cron_expr
    status["updatedAt"] = updated.get("updatedAt")
    status["triggerAt"] = trigger_time.strftime("%Y-%m-%d %H:%M:%S JST")
    status["step"] = "waiting_for_trigger"
    write_status(status)

    wait_seconds = max(0, int((trigger_time - datetime.now(JST)).total_seconds()) + 10)
    time.sleep(wait_seconds)

    status["step"] = "polling_results"
    write_status(status)
    status["execution"] = poll_execution(WORKFLOW_ID, started_after_iso, timeout_seconds=180)

    status["step"] = "restoring"
    write_status(status)
    restore_target = request_json(f"/workflows/{WORKFLOW_ID}")
    restore_target["nodes"] = original_wf["nodes"]
    restore_target["connections"] = original_wf["connections"]
    restore_target["settings"] = original_wf.get("settings")
    restore_target["staticData"] = original_wf.get("staticData")
    restored = update_workflow(restore_target)
    status["restoredAt"] = restored.get("updatedAt")
    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
