#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


JST = timezone(timedelta(hours=9))
TS = datetime.now(JST).strftime("%Y%m%d_%H%M%S")

API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "n8n"
STATUS_PATH = ROOT / "data" / "workspace" / "n8n_schedule_fix_status.json"

WORKFLOWS = {
    "SG2teXHO94CvzCoU": "Daily Promises Report (23:00 JST)",
    "vo3Yhdb8M97JQHfx": "Daily System Health Check (09:00 JST)",
    "0qNc6FdnxdDFICGe": "Email RAG Ingest (Nightly 02:00 JST)",
    "sYuks4F4aDvENqpl": "P016 Email Report (Daily 21:00 JST)",
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


def backup_workflow(wf: dict) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"workflow_{wf['id']}_{TS}.json"
    path.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def patch_promises(wf: dict) -> list[str]:
    changes = []
    for node in wf["nodes"]:
        if node["name"] == "PROMISES.md読み込み":
            new_command = "cat /workspace/PROMISES.md"
            if node["parameters"].get("command") != new_command:
                node["parameters"]["command"] = new_command
                changes.append("read PROMISES.md directly from /workspace")
    return changes


def patch_health_check(wf: dict) -> list[str]:
    changes = []
    for node in wf["nodes"]:
        if node["name"] == "copy_script":
            new_command = (
                "docker cp /workspace/daily_health_check.py "
                "clawstack-unified-clawdbot-gateway-1:/home/node/clawd/daily_health_check.py 2>&1 || true"
            )
            if node["parameters"].get("command") != new_command:
                node["parameters"]["command"] = new_command
                changes.append("use /workspace/daily_health_check.py as copy source")
        elif node["name"] == "format_message":
            new_js = "\n".join(
                [
                    "var first = $input.first();",
                    "var raw = ((first && first.json && (first.json.stdout || first.json.stderr)) || '').slice(0, 3500);",
                    "var hasWarn = raw.includes('WARN');",
                    "var warnCount = (raw.match(/WARN/g) || []).length;",
                    "var prefix = hasWarn ? '[WARNING ' + warnCount + ' items] ' : '[OK] ';",
                    "var now = new Date().toLocaleString('ja-JP', {timeZone: 'Asia/Tokyo'});",
                    "var text = prefix + 'Daily Health Check ' + now + String.fromCharCode(10) + raw;",
                    "return [{json: {text: text, has_warn: hasWarn}}];",
                ]
            )
            if node["parameters"].get("jsCode") != new_js:
                node["parameters"]["jsCode"] = new_js
                changes.append("fix format_message syntax to use $input.first()")
    return changes


def patch_email_rag(wf: dict) -> list[str]:
    changes = []
    for node in wf["nodes"]:
        if node["name"] == "telegram_notify":
            body = node["parameters"].get("body", {})
            desired = "8173025084"
            if body.get("chat_id") != desired:
                body["chat_id"] = desired
                node["parameters"]["body"] = body
                changes.append("set telegram_notify chat_id to 8173025084")
    return changes


def patch_p016(wf: dict) -> list[str]:
    changes = []
    for node in wf["nodes"]:
        if node["name"] == "build_todo_report":
            new_command = (
                "docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "
                "\"python3 /home/node/clawd/generate_todo_report.py --months-back 6 --limit 10\""
            )
            if node["parameters"].get("command") != new_command:
                node["parameters"]["command"] = new_command
                changes.append("use generate_todo_report.py with default last-6-month rule")
        elif node["name"] == "format_message":
            new_js = "\n".join(
                [
                    "var NL = String.fromCharCode(10);",
                    "var now = new Date().toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });",
                    "var raw = (($input.first() && $input.first().json && $input.first().json.stdout) || '').trim();",
                    "var summary = '直近6か月の未対応案件は見つかりませんでした。';",
                    "try {",
                    "  var parsed = JSON.parse(raw);",
                    "  summary = parsed.summary || summary;",
                    "} catch (e) {",
                    "  summary = raw || ('P016 report parse error: ' + e.message);",
                    "}",
                    "var parts = ['P016 Email ToDo Daily [' + now + ']', '', summary, '', 'ルール: 既定は直近6か月。さらに過去が必要なら範囲を広げて再送します。'];",
                    "return [{ json: { text: parts.join(NL) } }];",
                ]
            )
            if node["parameters"].get("jsCode") != new_js:
                node["parameters"]["jsCode"] = new_js
                changes.append("update format_message for last-6-month default rule")
    return changes


PATCHERS = {
    "SG2teXHO94CvzCoU": patch_promises,
    "vo3Yhdb8M97JQHfx": patch_health_check,
    "0qNc6FdnxdDFICGe": patch_email_rag,
    "sYuks4F4aDvENqpl": patch_p016,
}


def update_workflow(wf: dict) -> dict:
    payload = {k: v for k, v in wf.items() if k in {"name", "nodes", "connections", "settings", "staticData"}}
    return request_json(f"/workflows/{wf['id']}", method="PUT", payload=payload)


def main() -> None:
    status = {
        "startedAt": now_jst(),
        "step": "inspect_and_patch",
        "results": [],
    }
    write_status(status)

    for wf_id, wf_name in WORKFLOWS.items():
        wf = request_json(f"/workflows/{wf_id}")
        backup = backup_workflow(wf)
        changes = PATCHERS[wf_id](wf)
        updated = None
        if changes:
            updated = update_workflow(wf)
        status["results"].append(
            {
                "workflowId": wf_id,
                "name": wf_name,
                "backup": str(backup),
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
