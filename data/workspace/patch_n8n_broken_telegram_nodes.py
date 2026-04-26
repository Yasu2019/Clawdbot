#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "n8n_broken_telegram_patch_status.json"

TARGETS = {
    "zO38wIUIoZJ7KsyS": "Daily AI Scout (新AI・ツール探索)",
    "0qNc6FdnxdDFICGe": "Email RAG Ingest (Nightly 02:00 JST)",
}


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


def backup_workflow(wf: dict, suffix: str) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_{suffix}_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def update_workflow(wf: dict) -> dict:
    payload = {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{wf['id']}", method="PUT", payload=payload)


def patch_ai_scout(node: dict) -> bool:
    desired = {
        "method": "POST",
        "url": "https://api.telegram.org/bot8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4/sendMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "8173025084"},
                {"name": "text", "value": "={{ $json.message }}"},
            ]
        },
        "options": {},
    }
    if node.get("parameters") != desired:
        node["parameters"] = desired
        return True
    return False


def patch_email_rag(node: dict) -> bool:
    desired = {
        "method": "POST",
        "url": "https://api.telegram.org/bot8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4/sendMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "8173025084"},
                {
                    "name": "text",
                    "value": "={{ \"Email ingest finished\\n\\nQdrant: \" + $node[\"phase12_qdrant\"].json.stdout.split(\"\\n\").slice(-3).join(\"\\n\") + \"\\nMeilisearch: \" + $node[\"phase3_meilisearch\"].json.stdout.split(\"\\n\").slice(-2).join(\"\\n\") + \"\\nSQLite/Gmail: \" + $node[\"phase4_sqlite_search\"].json.stdout.split(\"\\n\").slice(-2).join(\"\\n\") }}",
                },
            ]
        },
        "options": {},
    }
    if node.get("parameters") != desired:
        node["parameters"] = desired
        return True
    return False


def main() -> None:
    status = {"startedAt": now_jst(), "results": [], "step": "patching"}
    write_status(status)
    for wf_id, name in TARGETS.items():
        wf = request_json(f"/workflows/{wf_id}")
        backup = backup_workflow(wf, "fix_telegram")
        changed = False
        for node in wf["nodes"]:
            if wf_id == "zO38wIUIoZJ7KsyS" and node["name"] == "Telegram Notify":
                changed = patch_ai_scout(node) or changed
            if wf_id == "0qNc6FdnxdDFICGe" and node["name"] == "telegram_notify":
                changed = patch_email_rag(node) or changed
        updated = update_workflow(wf) if changed else None
        status["results"].append(
            {
                "workflowId": wf_id,
                "name": name,
                "backup": backup,
                "changed": changed,
                "updatedAt": updated.get("updatedAt") if updated else None,
            }
        )
        write_status(status)
    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
