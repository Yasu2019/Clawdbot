#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "n8n_gmail_patch_status.json"
JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
RECIPIENT = "y.suzuki.hk@gmail.com"

WORKFLOWS = {
    "sYuks4F4aDvENqpl": {
        "label": "P016 Email Report (Daily 21:00 JST)",
        "subject": "P016 Email ToDo Daily",
        "source": "format_message",
        "payload": "prepare_gmail_payload",
        "position": [1450, 0],
    },
    "SG2teXHO94CvzCoU": {
        "label": "Daily Promises Report (23:00 JST)",
        "subject": "Daily Promises Report",
        "source": "メッセージ整形",
        "payload": "prepare_gmail_payload",
        "position": [1250, 0],
    },
    "vo3Yhdb8M97JQHfx": {
        "label": "Daily System Health Check (09:00 JST)",
        "subject": "Daily System Health Check",
        "source": "format_message",
        "payload": "prepare_gmail_payload",
        "position": [1350, 0],
    },
    "0qNc6FdnxdDFICGe": {
        "label": "Email RAG Ingest (Nightly 02:00 JST)",
        "subject": "Email RAG Ingest",
        "source": "phase4_sqlite_search",
        "payload": "prepare_gmail_payload",
        "position": [1250, -120],
    },
}


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def backup_workflow(wf: dict) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_gmail_patch_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def ensure_connection(wf: dict, source_name: str, target_name: str) -> bool:
    wf.setdefault("connections", {})
    wf["connections"].setdefault(source_name, {"main": [[]]})
    outputs = wf["connections"][source_name]["main"]
    if not outputs:
        outputs.append([])
    first_output = outputs[0]
    if not any(conn.get("node") == target_name for conn in first_output):
        first_output.append({"node": target_name, "type": "main", "index": 0})
        return True
    return False


def remove_connection(wf: dict, source_name: str, target_name: str) -> bool:
    source = wf.get("connections", {}).get(source_name)
    if not source:
        return False
    changed = False
    for output in source.get("main", []) or []:
        original_len = len(output)
        output[:] = [conn for conn in output if conn.get("node") != target_name]
        if len(output) != original_len:
            changed = True
    return changed


def ensure_prepare_node(wf: dict, subject: str, source_name: str, position: list[int]) -> list[str]:
    changes: list[str] = []
    node_name = "prepare_gmail_payload"
    existing = next((node for node in wf["nodes"] if node["name"] == node_name), None)
    js_code = (
        "const body = (($json.text || $json.summary || $json.stdout || '') + '').trim();\n"
        "const encode = (value) => Buffer.from((value || '') + '', 'utf8')\n"
        "  .toString('base64')\n"
        "  .replace(/\\+/g, '-')\n"
        "  .replace(/\\//g, '_')\n"
        "  .replace(/=+$/g, '');\n"
        f"return [{{ json: {{ subject_b64: encode({json.dumps(subject)}), body_b64: encode(body), text: body }} }}];"
    )
    node_payload = {
        "id": "prepare-gmail-payload",
        "name": node_name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
        "parameters": {
            "jsCode": js_code,
        },
    }

    if existing is None:
        wf["nodes"].append(node_payload)
        changes.append("add prepare_gmail_payload node")
    else:
        if existing.get("parameters", {}).get("jsCode") != js_code:
            existing["parameters"]["jsCode"] = js_code
            changes.append("update prepare_gmail_payload code")
        existing["type"] = "n8n-nodes-base.code"
        existing["typeVersion"] = 2
        existing["position"] = position

    if ensure_connection(wf, source_name, node_name):
        changes.append(f"connect {source_name} -> prepare_gmail_payload")
    if remove_connection(wf, source_name, "gmail_send"):
        changes.append(f"disconnect {source_name} -> gmail_send")
    return changes


def ensure_gmail_node(wf: dict, payload_name: str, position: list[int]) -> list[str]:
    changes: list[str] = []
    node_name = "gmail_send"
    existing = next((node for node in wf["nodes"] if node["name"] == node_name), None)
    command = (
        f"node /workspace/scripts/send_allowed_gmail_from_b64.js {RECIPIENT} "
        "{{$json.subject_b64}} {{$json.body_b64}}"
    )
    node_payload = {
        "id": "gmail-send-report",
        "name": node_name,
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": position,
        "parameters": {
            "executeOnce": True,
            "command": command,
        },
    }

    if existing is None:
        wf["nodes"].append(node_payload)
        changes.append("add gmail_send node")
    else:
        if existing.get("parameters", {}).get("command") != command:
            existing["parameters"]["command"] = command
            changes.append("update gmail_send command")
        existing["type"] = "n8n-nodes-base.executeCommand"
        existing["typeVersion"] = 1
        existing["position"] = position

    if ensure_connection(wf, payload_name, node_name):
        changes.append(f"connect {payload_name} -> gmail_send")
    return changes


def update_workflow(wf: dict) -> dict:
    payload = {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{wf['id']}", method="PUT", payload=payload)


def main() -> None:
    status = {
        "startedAt": now_jst(),
        "step": "patching",
        "recipient": RECIPIENT,
        "results": [],
    }
    write_status(status)

    for wf_id, cfg in WORKFLOWS.items():
        wf = request_json(f"/workflows/{wf_id}")
        backup_path = backup_workflow(wf)
        changes: list[str] = []
        changes.extend(
            ensure_prepare_node(
                wf,
                cfg["subject"],
                cfg["source"],
                [cfg["position"][0] - 260, cfg["position"][1]],
            )
        )
        changes.extend(ensure_gmail_node(wf, cfg["payload"], cfg["position"]))
        updated = None
        if changes:
            updated = update_workflow(wf)
        status["results"].append(
            {
                "workflowId": wf_id,
                "name": cfg["label"],
                "backup": backup_path,
                "changes": changes,
                "updatedAt": updated.get("updatedAt") if updated else None,
            }
        )
        write_status(status)

    status["finishedAt"] = now_jst()
    status["step"] = "completed"
    write_status(status)


if __name__ == "__main__":
    main()
