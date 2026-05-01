#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data" / "workspace" / "restore_missing_critical_n8n_workflows_20260429_status.json"
BACKUP_DIR = ROOT / "backups" / "n8n"
HELPER_PATH = ROOT / "data" / "workspace" / "repair_telegram_n8n_schedules_20260429.py"

TARGETS = [
    {
        "key": "promises",
        "source_id": "SG2teXHO94CvzCoU",
        "name": "Daily Promises Report (23:00 JST)",
        "cron": "0 23 * * *",
    },
    {
        "key": "health_check",
        "source_id": "vo3Yhdb8M97JQHfx",
        "name": "Daily System Health Check (09:00 JST)",
        "cron": "0 9 * * *",
    },
    {
        "key": "email_rag",
        "source_id": "0qNc6FdnxdDFICGe",
        "name": "Email RAG Ingest (Nightly 02:00 JST)",
        "cron": "0 2 * * *",
    },
    {
        "key": "trend_opportunity",
        "source_id": "7CpooDw45JT71deJ",
        "name": "Daily Trend Opportunity Report (20:30 JST)",
        "cron": "30 20 * * *",
    },
]


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_helper() -> Any:
    spec = importlib.util.spec_from_file_location("n8n_repair_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workflow_payload(wf: dict[str, Any], include_active: bool = False) -> dict[str, Any]:
    keys = {"name", "nodes", "connections", "settings", "staticData"}
    if include_active:
        keys.add("active")
    return {key: value for key, value in wf.items() if key in keys}


def workflow_crons(wf: dict[str, Any]) -> list[str]:
    crons: list[str] = []
    for node in wf.get("nodes", []) or []:
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        intervals = (((node.get("parameters") or {}).get("rule") or {}).get("interval") or [])
        for interval in intervals:
            expr = interval.get("expression")
            if expr:
                crons.append(str(expr))
    return crons


def validate_workflow(wf: dict[str, Any], expected_cron: str) -> list[str]:
    problems: list[str] = []
    nodes = wf.get("nodes") or []
    if not nodes:
        problems.append("workflow has no nodes")
    crons = workflow_crons(wf)
    if expected_cron not in crons:
        problems.append(f"expected cron {expected_cron!r} not found; found={crons!r}")
    if not isinstance(wf.get("connections"), dict):
        problems.append("connections is not an object")
    return problems


def find_current_by_name(helper: Any, name: str) -> dict[str, Any] | None:
    for wf in helper.list_workflows():
        if wf.get("name") != name:
            continue
        workflow_id = wf.get("id")
        return helper.get_workflow(str(workflow_id)) if workflow_id else wf
    return None


def latest_active_backup(source_id: str) -> tuple[dict[str, Any], str]:
    candidates = sorted(BACKUP_DIR.glob(f"workflow_{source_id}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    best_inactive: tuple[dict[str, Any], str] | None = None
    for path in candidates:
        try:
            wf = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if best_inactive is None:
            best_inactive = (wf, str(path))
        if wf.get("active") is True:
            return wf, str(path)
    if best_inactive:
        return best_inactive
    raise RuntimeError(f"no backup found for workflow_{source_id}_*.json")


def backup_current_api_list(helper: Any) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"workflows_current_pre_critical_restore_{ts}.json"
    rows = helper.list_workflows()
    details = []
    for row in rows:
        workflow_id = row.get("id")
        details.append(helper.get_workflow(str(workflow_id)) if workflow_id else row)
    path.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def restore_target(helper: Any, target: dict[str, str]) -> dict[str, Any]:
    existing = helper.get_workflow(target["source_id"]) or find_current_by_name(helper, target["name"])
    if existing:
        helper.set_schedule_cron(existing, target["cron"])
        backup = helper.backup_workflow(existing, f"pre_critical_restore_{target['key']}")
        update = helper.request_json(f"/workflows/{existing['id']}", "PUT", workflow_payload(existing))
        activation = helper.activate_workflow(str(existing["id"]))
        detail = helper.get_workflow(str(existing["id"])) or existing
        return {
            "status": "already_present",
            "workflowId": existing["id"],
            "name": existing.get("name"),
            "backup": backup,
            "updatedAt": update.get("updatedAt"),
            "active": detail.get("active"),
            "crons": workflow_crons(detail),
            "activation": activation,
        }

    source, source_backup = latest_active_backup(target["source_id"])
    source["name"] = target["name"]
    helper.set_schedule_cron(source, target["cron"])
    pre_problems = validate_workflow(source, target["cron"])
    if pre_problems:
        return {
            "status": "skipped_validation_failed",
            "sourceBackup": source_backup,
            "problems": pre_problems,
        }

    created = helper.unwrap_response(helper.request_json("/workflows", "POST", workflow_payload(source, include_active=False)))
    created_id = str(created.get("id") or "")
    detail = helper.get_workflow(created_id) if created_id else None
    post_problems = validate_workflow(detail or created, target["cron"])
    activation: dict[str, Any] = {}
    if created_id and not post_problems:
        activation = helper.activate_workflow(created_id)
        detail = helper.get_workflow(created_id) or detail

    return {
        "status": "restored" if created_id and not post_problems else "created_but_not_activated",
        "sourceBackup": source_backup,
        "workflowId": created_id or None,
        "name": (detail or created).get("name"),
        "active": (detail or created).get("active"),
        "crons": workflow_crons(detail or created),
        "nodeCount": len((detail or created).get("nodes") or []),
        "postValidationProblems": post_problems,
        "activation": activation,
    }


def main() -> int:
    helper = load_helper()
    status: dict[str, Any] = {
        "startedAt": now_jst(),
        "stage": "running",
        "targets": [target["name"] for target in TARGETS],
        "results": {},
    }
    save_json(STATUS_PATH, status)
    status["preRestoreApiBackup"] = backup_current_api_list(helper)
    save_json(STATUS_PATH, status)

    for target in TARGETS:
        status["results"][target["key"]] = restore_target(helper, target)
        save_json(STATUS_PATH, status)

    current = []
    for wf in helper.list_workflows():
        detail = helper.get_workflow(str(wf.get("id"))) or wf
        current.append(
            {
                "id": detail.get("id"),
                "name": detail.get("name"),
                "active": detail.get("active"),
                "crons": workflow_crons(detail),
                "nodeCount": len(detail.get("nodes") or []),
            }
        )
    status["currentWorkflows"] = current
    status["stage"] = "completed"
    status["finishedAt"] = now_jst()
    save_json(STATUS_PATH, status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
