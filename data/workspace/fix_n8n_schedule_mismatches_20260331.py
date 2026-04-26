#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")

API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "n8n_schedule_mismatch_fix_20260331.json"

WORKFLOWS = {
    "7CpooDw45JT71deJ": {
        "name": "Daily Trend Opportunity Report (20:30 JST)",
        "expected_cron": "30 20 * * *",
    },
    "0qNc6FdnxdDFICGe": {
        "name": "Email RAG Ingest (Nightly 02:00 JST)",
        "expected_cron": "0 2 * * *",
    },
    "vo3Yhdb8M97JQHfx": {
        "name": "Daily System Health Check (09:00 JST)",
        "expected_cron": "0 9 * * *",
    },
}


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def backup_workflow(workflow: dict[str, Any], label: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{workflow['id']}_{label}_{TS}.json"
    path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def extract_cron_expressions(workflow: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for node in workflow.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        params = node.get("parameters", {}) or {}
        rule = params.get("rule") or {}
        for item in rule.get("interval") or []:
            if isinstance(item, dict) and item.get("field") == "cronExpression":
                rows.append({"node": node.get("name") or "", "expression": str(item.get("expression") or "")})
    return rows


def patch_workflow_cron(workflow: dict[str, Any], expected_cron: str) -> tuple[list[dict[str, str]], bool]:
    before = extract_cron_expressions(workflow)
    changed = False
    for node in workflow.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        params = node.get("parameters", {}) or {}
        rule = params.get("rule") or {}
        intervals = rule.get("interval") or []
        for item in intervals:
            if isinstance(item, dict) and item.get("field") == "cronExpression":
                if item.get("expression") != expected_cron:
                    item["expression"] = expected_cron
                    changed = True
    return before, changed


def update_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in workflow.items()
        if key in {"name", "nodes", "connections", "settings", "staticData"}
    }
    return request_json(f"/workflows/{workflow['id']}", method="PUT", payload=payload)


def main() -> None:
    status: dict[str, Any] = {
        "startedAt": now_jst(),
        "step": "inspect_and_fix",
        "results": [],
    }
    write_status(status)

    for workflow_id, meta in WORKFLOWS.items():
        workflow = request_json(f"/workflows/{workflow_id}")
        backup = backup_workflow(workflow, "pre_schedule_mismatch_fix")
        before, changed = patch_workflow_cron(workflow, meta["expected_cron"])
        after = extract_cron_expressions(workflow)
        updated = update_workflow(workflow) if changed else None
        status["results"].append(
            {
                "workflowId": workflow_id,
                "name": meta["name"],
                "active": workflow.get("active"),
                "backup": str(backup),
                "before": before,
                "after": after,
                "expectedCron": meta["expected_cron"],
                "changed": changed,
                "apiUpdatedAt": (updated or {}).get("updatedAt"),
            }
        )
        write_status(status)

    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
