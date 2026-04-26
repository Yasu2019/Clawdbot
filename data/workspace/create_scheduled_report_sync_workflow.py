#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


WORKFLOW_NAME = "Sync Scheduled Reports to DB (Every 30m)"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "scheduled_report_sync_workflow_status.json"
JST = timezone(timedelta(hours=9))
BROWSER_ID = "clawstack001"
ACTIVE_MODE = "api_key"
ACTIVE_COOKIE = ""


def load_env_value(name: str) -> str:
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    env_path = ROOT / ".env"
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


API_BASE = "http://127.0.0.1:5679/api/v1"
REST_BASE = "http://127.0.0.1:5679/rest"
API_KEY = load_env_value("N8N_API_KEY") or "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
N8N_LOGIN_EMAIL = load_env_value("N8N_EMAIL") or "y.suzuki.hk@gmail.com"
N8N_LOGIN_PASSWORD = load_env_value("N8N_PASSWORD") or "Foxconnjpn75"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    global ACTIVE_MODE, ACTIVE_COOKIE
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    auth_attempts: list[tuple[str, str, dict[str, str]]] = []
    if ACTIVE_MODE == "cookie" and ACTIVE_COOKIE:
        auth_attempts.append(
            (
                "cookie",
                REST_BASE,
                {"Cookie": f"n8n-auth={ACTIVE_COOKIE}", "browser-id": BROWSER_ID, "Content-Type": "application/json"},
            )
        )
    auth_attempts.extend(
        [
            ("api_key", API_BASE, {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}),
            ("api_key", REST_BASE, {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}),
        ]
    )
    last_error: Exception | None = None
    for mode, base, headers in auth_attempts:
        req = urllib.request.Request(f"{base}{path}", data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                ACTIVE_MODE = mode
                return json.load(resp)
        except Exception as exc:
            last_error = exc
    login_req = urllib.request.Request(
        f"{REST_BASE}/login",
        data=json.dumps({"emailOrLdapLoginId": N8N_LOGIN_EMAIL, "password": N8N_LOGIN_PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json", "browser-id": BROWSER_ID},
        method="POST",
    )
    with urllib.request.urlopen(login_req, timeout=15) as resp:
        for header in resp.headers.get_all("Set-Cookie") or []:
            if "n8n-auth=" in header:
                ACTIVE_COOKIE = header.split("n8n-auth=", 1)[1].split(";", 1)[0]
                ACTIVE_MODE = "cookie"
                break
    if not ACTIVE_COOKIE:
        raise RuntimeError("n8n login did not return n8n-auth cookie")
    req = urllib.request.Request(
        f"{REST_BASE}{path}",
        data=body,
        headers={"Cookie": f"n8n-auth={ACTIVE_COOKIE}", "browser-id": BROWSER_ID, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
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
                "name": "Every 30 Minutes",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "parameters": {
                    "rule": {
                        "interval": [
                            {"field": "cronExpression", "expression": "*/30 * * * *"}
                        ]
                    }
                },
            },
            {
                "id": "node-sync",
                "name": "Sync Scheduled Reports",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [260, 0],
                "parameters": {
                    "command": "python3 /workspace/scheduled_report_search.py sync --limit-executions 20",
                },
            },
        ],
        "connections": {
            "Every 30 Minutes": {
                "main": [[{"node": "Sync Scheduled Reports", "type": "main", "index": 0}]]
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
        status["backup"] = backup_workflow(existing, "scheduled_report_sync_update")
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
