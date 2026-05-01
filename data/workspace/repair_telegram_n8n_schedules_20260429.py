#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "repair_telegram_n8n_schedules_20260429_status.json"
OPENCLAW_CONFIG = ROOT / "data" / "state" / "openclaw.json"
API_BASE = os.environ.get("N8N_API_BASE", "http://127.0.0.1:5679/api/v1").rstrip("/")
BROWSER_ID = "repair-telegram-n8n-20260429"
COOKIE_CACHE: str | None = None


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def load_env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    env_path = ROOT / ".env"
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw_value = line.split("=", 1)
            if key.strip() == name:
                return raw_value.strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def load_telegram_config() -> tuple[str, str]:
    cfg = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
    telegram = ((cfg.get("channels") or {}).get("telegram") or {})
    token = str(telegram.get("botToken") or load_env_value("TELEGRAM_BOT_TOKEN")).strip()
    chat_ids = telegram.get("allowFrom") or []
    chat_id = str(load_env_value("TELEGRAM_CHAT_ID") or (chat_ids[0] if chat_ids else "")).strip()
    if not token or not chat_id:
        raise RuntimeError("Telegram bot token or chat id is missing")
    return token, chat_id


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = load_env_value("N8N_API_KEY")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
        try:
            req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except Exception:
            pass

    cookie = fetch_login_cookie()
    rest_base = API_BASE.replace("/api/v1", "/rest")
    req = urllib.request.Request(
        f"{rest_base}{path}",
        data=data,
        headers={"Cookie": f"n8n-auth={cookie}", "browser-id": BROWSER_ID, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def fetch_login_cookie() -> str:
    global COOKIE_CACHE
    if COOKIE_CACHE:
        return COOKIE_CACHE
    email_candidates = [
        load_env_value("N8N_EMAIL"),
        "y.suzuki.hk@gmail.com",
        load_env_value("CLAWSTACK_ADMIN_EMAIL"),
    ]
    password = load_env_value("N8N_PASSWORD") or load_env_value("n8n_PW")
    if not password:
        raise RuntimeError("n8n password is missing")
    rest_base = API_BASE.replace("/api/v1", "/rest")
    last_error: Exception | None = None
    for email in [candidate for candidate in email_candidates if candidate]:
        body = json.dumps({"emailOrLdapLoginId": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{rest_base}/login",
            data=body,
            headers={"Content-Type": "application/json", "browser-id": BROWSER_ID},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                for header in resp.headers.get_all("Set-Cookie") or []:
                    if "n8n-auth=" in header:
                        COOKIE_CACHE = header.split("n8n-auth=", 1)[1].split(";", 1)[0]
                        return COOKIE_CACHE
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("n8n login did not return auth cookie")


def backup_workflow(wf: dict[str, Any], suffix: str) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"workflow_{wf['id']}_{suffix}_{ts}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def workflow_payload(wf: dict[str, Any], include_active: bool = False) -> dict[str, Any]:
    keys = {"name", "nodes", "connections", "settings", "staticData"}
    if include_active:
        keys.add("active")
    return {key: value for key, value in wf.items() if key in keys}


def unwrap_response(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    return data if isinstance(data, dict) else response


def activate_workflow(workflow_id: str) -> dict[str, Any]:
    detail = unwrap_response(request_json(f"/workflows/{workflow_id}"))
    version_id = detail.get("versionId")
    if not version_id:
        return {"active": detail.get("active"), "reason": "versionId missing"}
    activated = unwrap_response(request_json(f"/workflows/{workflow_id}/activate", "POST", {"versionId": version_id}))
    return {"active": activated.get("active"), "versionId": version_id}


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    try:
        return unwrap_response(request_json(f"/workflows/{workflow_id}"))
    except Exception:
        return None


def list_workflows() -> list[dict[str, Any]]:
    data = request_json("/workflows?limit=100")
    rows = data.get("data") or []
    if isinstance(rows, dict):
        rows = rows.get("results") or []
    return rows if isinstance(rows, list) else []


def find_workflow_by_name(name: str) -> dict[str, Any] | None:
    for wf in list_workflows():
        if wf.get("name") == name and wf.get("id"):
            return get_workflow(str(wf["id"])) or wf
    return None


def load_latest_backup(prefix: str) -> tuple[dict[str, Any], str]:
    candidates = sorted(BACKUP_DIR.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError(f"no backup found for {prefix}")
    return json.loads(candidates[0].read_text(encoding="utf-8")), str(candidates[0])


def set_schedule_cron(wf: dict[str, Any], cron: str) -> bool:
    changed = False
    for node in wf.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        desired = {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}}
        if node.get("parameters") != desired:
            node["parameters"] = desired
            changed = True
    return changed


def ensure_connection(wf: dict[str, Any], source: str, target: str) -> bool:
    wf.setdefault("connections", {})
    wf["connections"].setdefault(source, {"main": [[]]})
    outputs = wf["connections"][source].setdefault("main", [[]])
    if not outputs:
        outputs.append([])
    if not any(conn.get("node") == target for conn in outputs[0]):
        outputs[0].append({"node": target, "type": "main", "index": 0})
        return True
    return False


def upsert_node(wf: dict[str, Any], node: dict[str, Any]) -> bool:
    for existing in wf.get("nodes", []):
        if existing.get("name") == node["name"]:
            if existing != node:
                existing.clear()
                existing.update(node)
                return True
            return False
    wf.setdefault("nodes", []).append(node)
    return True


def patch_p016() -> dict[str, Any]:
    wf = get_workflow("sYuks4F4aDvENqpl") or find_workflow_by_name("P016 Email Report (Daily 21:00 JST)")
    source_backup = ""
    restored = False
    if not wf:
        wf, source_backup = load_latest_backup("workflow_sYuks4F4aDvENqpl")
        restored = True
    backup = backup_workflow(wf, "pre_due_telegram_repair")
    token, chat_id = load_telegram_config()
    changed = set_schedule_cron(wf, "0 21 * * *")

    command = (
        "docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "
        "\"python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db "
        "tasks-context '納期 今週 未回答' --limit 10\""
    )
    for node in wf.get("nodes", []):
        if node.get("name") == "build_todo_report":
            params = node.setdefault("parameters", {})
            if params.get("command") != command:
                params["command"] = command
                changed = True

    format_node = {
        "id": "format-due-telegram-payload",
        "name": "format_due_telegram_payload",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1180, 180],
        "parameters": {
            "jsCode": (
                "const raw = String($json.stdout || $json.text || '').trim();\n"
                "let parsed = {};\n"
                "try { parsed = JSON.parse(raw); } catch (e) { parsed = {}; }\n"
                "const summary = String(parsed.summary || raw || '納期確認データは取得できませんでした。').trim();\n"
                "const count = Number(parsed.result_count || 0);\n"
                "const message = `Gmail納期確認 定時レポート\\n対象: 今週期限・未回答\\n件数: ${count}件\\n\\n${summary}`;\n"
                "return [{ json: { message, text: message, summary, result_count: count } }];"
            )
        },
    }
    telegram_node = {
        "id": "telegram-due-notify",
        "name": "telegram_due_notify",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1450, 180],
        "parameters": {
            "method": "POST",
            "url": f"https://api.telegram.org/bot{token}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": chat_id},
                    {"name": "text", "value": "={{ $json.message }}"},
                ]
            },
            "options": {},
        },
    }
    changed = upsert_node(wf, format_node) or changed
    changed = upsert_node(wf, telegram_node) or changed
    changed = ensure_connection(wf, "build_todo_report", "format_due_telegram_payload") or changed
    changed = ensure_connection(wf, "format_due_telegram_payload", "telegram_due_notify") or changed
    if restored:
        created = unwrap_response(request_json("/workflows", "POST", workflow_payload(wf, include_active=True)))
        activation = activate_workflow(str(created.get("id"))) if created.get("id") else {}
        return {
            "workflowId": created.get("id"),
            "backup": backup,
            "sourceBackup": source_backup,
            "changed": True,
            "restored": True,
            "activation": activation,
            "updatedAt": created.get("updatedAt"),
        }
    updated = request_json(f"/workflows/{wf['id']}", "PUT", workflow_payload(wf)) if changed else {}
    return {"workflowId": wf["id"], "backup": backup, "changed": changed, "restored": False, "updatedAt": updated.get("updatedAt")}


def restore_ai_scout_if_missing() -> dict[str, Any]:
    existing = get_workflow("zO38wIUIoZJ7KsyS") or find_workflow_by_name("Daily AI Scout (新AI・ツール探索)")
    if existing:
        backup = backup_workflow(existing, "pre_ai_scout_schedule_repair")
        changed = set_schedule_cron(existing, "40 9 * * *")
        updated = request_json(f"/workflows/{existing['id']}", "PUT", workflow_payload(existing)) if changed else {}
        return {"workflowId": existing["id"], "backup": backup, "changed": changed, "restored": False, "updatedAt": updated.get("updatedAt")}

    try:
        source, source_backup = load_latest_backup("workflow_zO38wIUIoZJ7KsyS")
    except RuntimeError as exc:
        return {"restored": False, "reason": str(exc)}
    set_schedule_cron(source, "40 9 * * *")
    payload = workflow_payload(source, include_active=True)
    created = unwrap_response(request_json("/workflows", "POST", payload))
    activation = activate_workflow(str(created.get("id"))) if created.get("id") else {}
    return {"restored": True, "sourceBackup": source_backup, "newWorkflowId": created.get("id"), "name": created.get("name"), "activation": activation}


def main() -> int:
    status: dict[str, Any] = {"startedAt": now_jst(), "stage": "running", "results": {}}
    save_json(STATUS_PATH, status)
    status["results"]["p016"] = patch_p016()
    save_json(STATUS_PATH, status)
    status["results"]["aiScout"] = restore_ai_scout_if_missing()
    status["stage"] = "completed"
    status["finishedAt"] = now_jst()
    save_json(STATUS_PATH, status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
