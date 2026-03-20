#!/usr/bin/env python3
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "n8n_trigger_once_status.json"

TARGETS = {
    "SG2teXHO94CvzCoU": "Daily Promises Report (23:00 JST)",
    "sYuks4F4aDvENqpl": "P016 Email Report (Daily 21:00 JST)",
}


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
    raise RuntimeError(f"scheduleTrigger not found for workflow {wf['id']}")


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
    status = {
        "startedAt": now_jst(),
        "targets": [],
        "step": "prepare",
    }
    write_status(status)

    trigger_time = datetime.now(JST).replace(second=0, microsecond=0) + timedelta(minutes=2)
    cron_expr = f"{trigger_time.minute} {trigger_time.hour} * * *"
    started_after_iso = datetime.now(timezone.utc).isoformat()

    originals: dict[str, dict] = {}
    for workflow_id, name in TARGETS.items():
        wf = request_json(f"/workflows/{workflow_id}")
        originals[workflow_id] = wf
        backup_path = backup_workflow(wf, "pre_trigger_once")
        node = schedule_node(wf)
        original_params = json.loads(json.dumps(node.get("parameters", {}), ensure_ascii=False))
        set_cron(node, cron_expr)
        updated = update_workflow(wf)
        status["targets"].append(
            {
                "workflowId": workflow_id,
                "name": name,
                "backup": backup_path,
                "originalSchedule": original_params,
                "temporaryCron": cron_expr,
                "updatedAt": updated.get("updatedAt"),
            }
        )
        write_status(status)

    status["step"] = "waiting_for_trigger"
    status["triggerAt"] = trigger_time.strftime("%Y-%m-%d %H:%M:%S JST")
    write_status(status)

    wait_seconds = max(0, int((trigger_time - datetime.now(JST)).total_seconds()) + 10)
    time.sleep(wait_seconds)

    status["step"] = "polling_results"
    write_status(status)

    for target in status["targets"]:
        execution = poll_execution(target["workflowId"], started_after_iso, timeout_seconds=180)
        target["execution"] = execution
        write_status(status)

    status["step"] = "restoring"
    write_status(status)
    for workflow_id, original in originals.items():
        restore_backup = backup_workflow(original, "restore_source")
        restored = update_workflow(original)
        for target in status["targets"]:
            if target["workflowId"] == workflow_id:
                target["restoredAt"] = restored.get("updatedAt")
                target["restoreBackup"] = restore_backup
        write_status(status)

    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
