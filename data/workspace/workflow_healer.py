#!/usr/bin/env python3
"""
workflow_healer.py — Autonomous n8n Workflow Self-Healer
========================================================
Runs every 15 minutes via n8n Schedule Trigger.

Strategy per failing workflow:
  Attempt 1-2 : Simple restart (disable → enable)
  Attempt 3-4 : LLM repair (Ollama qwen2.5-coder:7b fixes Code node JS)
  Attempt 5+  : Escalate to user (Telegram), stop auto-repair

All events are reported to Telegram.
State is persisted in REPAIR_STATE_FILE.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
N8N_BASE     = "http://n8n:5678/api/v1"
N8N_API_KEY  = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
OLLAMA_BASE  = "http://ollama:11434"
OLLAMA_MODEL = "qwen2.5-coder:7b"
TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CID = "8173025084"
REPAIR_STATE_FILE = Path("/home/node/clawd/repair_state.json")
LOG_FILE          = Path("/home/node/clawd/workflow_healer.log")

MAX_SIMPLE_ATTEMPTS = 2   # disable+enable restarts before trying LLM
MAX_LLM_ATTEMPTS    = 4   # LLM fix attempts before escalation
MAX_TOTAL_ATTEMPTS  = 5   # after this, notify only

# Workflows to exclude from monitoring (infrastructure monitors themselves)
EXCLUDE_WF_IDS = {"jVGXe2GEIz6RN7Z0"}  # Ingest Watchdog Supervisor

JST = timezone(timedelta(hours=9))


# ── Utility ───────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def http_json(url: str, method="GET", data=None, headers=None) -> dict:
    _headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
    if headers:
        _headers.update(headers)
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode(errors="replace")}
    except Exception as e:
        return {"_error": str(e)}


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = {"chat_id": TELEGRAM_CID, "text": text, "parse_mode": "HTML"}
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            pass
    except Exception as e:
        log(f"Telegram error: {e}")


def load_state() -> dict:
    if REPAIR_STATE_FILE.exists():
        try:
            return json.loads(REPAIR_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict):
    REPAIR_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ── n8n API helpers ───────────────────────────────────────────────────────────

def get_active_workflows() -> list:
    r = http_json(f"{N8N_BASE}/workflows?limit=100&active=true")
    return r.get("data", [])


def get_recent_executions(wf_id: str, limit=3) -> list:
    r = http_json(f"{N8N_BASE}/executions?workflowId={wf_id}&limit={limit}")
    return r.get("data", [])


def get_execution_error(wf_id: str) -> dict:
    """Returns {node_name, error_message, node_type, js_code} for the latest failed exec."""
    r = http_json(
        f"{N8N_BASE}/executions?workflowId={wf_id}&limit=1&includeData=true")
    execs = r.get("data", [])
    if not execs:
        return {}
    e = execs[0]
    rd = e.get("data", {}).get("resultData", {})
    result = {"status": e.get("status"), "startedAt": e.get("startedAt", "")}

    # Find the node that errored
    for node_name, runs in rd.get("runData", {}).items():
        for run in (runs or []):
            err = run.get("error")
            if err:
                result["node_name"] = node_name
                result["error_message"] = err.get("message", "")
                result["error_desc"] = err.get("description", "")
                return result
    top_err = rd.get("error", {})
    if top_err:
        result["node_name"] = top_err.get("node", {}).get("name", "?")
        result["error_message"] = top_err.get("message", "")
    return result


def get_node_code(wf_id: str, node_name: str) -> dict:
    """Fetch current code/params for a node."""
    r = http_json(f"{N8N_BASE}/workflows/{wf_id}")
    for node in r.get("nodes", []):
        if node.get("name") == node_name:
            return {
                "type": node.get("type", ""),
                "params": node.get("parameters", {}),
            }
    return {}


def restart_workflow(wf_id: str) -> bool:
    """Disable then re-enable a workflow to reset its trigger."""
    r1 = http_json(f"{N8N_BASE}/workflows/{wf_id}/deactivate", method="POST")
    time.sleep(2)
    r2 = http_json(f"{N8N_BASE}/workflows/{wf_id}/activate", method="POST")
    return "_error" not in r2


def apply_code_fix(wf_id: str, node_name: str, new_code: str) -> bool:
    """Patch the jsCode of a Code node in a workflow via PUT."""
    r = http_json(f"{N8N_BASE}/workflows/{wf_id}")
    if "_error" in r:
        return False
    nodes = r.get("nodes", [])
    patched = False
    for node in nodes:
        if node.get("name") == node_name:
            node["parameters"]["jsCode"] = new_code
            patched = True
    if not patched:
        return False
    allowed = {"name", "nodes", "connections", "settings", "staticData"}
    payload = {k: v for k, v in r.items() if k in allowed}
    result = http_json(f"{N8N_BASE}/workflows/{wf_id}",
                       method="PUT", data=payload)
    return "_error" not in result


# ── Ollama LLM repair ─────────────────────────────────────────────────────────

def llm_fix_js_code(node_name: str, current_code: str, error_msg: str) -> str | None:
    """
    Ask Ollama qwen2.5-coder:7b to fix a broken n8n Code node JS snippet.
    Returns fixed code string, or None on failure.
    """
    prompt = f"""You are fixing a broken n8n Code node (JavaScript).
Node name: {node_name}
Error: {error_msg}

Current broken code:
```javascript
{current_code}
```

Rules:
- Return ONLY the corrected JavaScript code, nothing else
- No markdown fences, no explanation
- Common cause: literal newline inside a string literal — use String.fromCharCode(10) instead
- Keep all logic intact, only fix the syntax/runtime error
- The code must work in n8n's JS sandbox (no require(), use $input, $node etc.)

Fixed code:"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
        code = resp.get("response", "").strip()
        # Strip markdown fences if LLM added them anyway
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(l for l in lines if not l.startswith("```")).strip()
        return code if code else None
    except Exception as e:
        log(f"Ollama error: {e}")
        return None


# ── Main heal loop ────────────────────────────────────────────────────────────

def heal():
    log("=== Workflow Healer started ===")
    state = load_state()
    workflows = get_active_workflows()
    log(f"Active workflows: {len(workflows)}")

    now_iso = datetime.now(timezone.utc).isoformat()
    messages = []  # Telegram summary lines
    state_changed = False

    for wf in workflows:
        wf_id   = wf["id"]
        wf_name = wf["name"]

        if wf_id in EXCLUDE_WF_IDS:
            continue

        execs = get_recent_executions(wf_id, limit=3)
        if not execs:
            continue

        # Check if the LATEST execution failed (not "any of last 3")
        # A single success means the workflow has recovered, regardless of history
        latest_status = execs[0].get("status", "")
        if latest_status not in ("error", "crashed"):
            # Clear state if workflow is now healthy
            if wf_id in state and state[wf_id].get("status") != "healthy":
                log(f"[{wf_name}] Recovered! (latest={latest_status})")
                messages.append(f"✅ <b>{wf_name}</b> — 回復しました")
                del state[wf_id]
                state_changed = True
            continue

        # Get or initialise repair state for this workflow
        ws = state.setdefault(wf_id, {
            "name": wf_name,
            "attempts": 0,
            "status": "failing",
            "first_seen": now_iso,
        })
        ws["name"] = wf_name
        ws["last_seen"] = now_iso

        attempts = ws.get("attempts", 0)
        err_info = get_execution_error(wf_id)
        err_msg  = err_info.get("error_message", "不明なエラー")
        node_name = err_info.get("node_name", "?")

        log(f"[{wf_name}] attempts={attempts} node={node_name} err={err_msg[:80]}")

        # ── Escalated: notify only ────────────────────────────────────────────
        if attempts >= MAX_TOTAL_ATTEMPTS:
            if ws.get("status") != "escalated":
                ws["status"] = "escalated"
                state_changed = True
                msg = (
                    f"🚨 <b>[修復断念] {wf_name}</b>\n"
                    f"自動修復を{attempts}回試みましたが失敗しました。\n"
                    f"ノード: <code>{node_name}</code>\n"
                    f"エラー: <code>{err_msg[:200]}</code>\n"
                    f"手動確認をお願いします: http://localhost:5679"
                )
                send_telegram(msg)
                messages.append(f"🚨 <b>{wf_name}</b> — 修復断念 (手動対応要)")
            continue

        # ── Attempt 1-2: simple restart ───────────────────────────────────────
        if attempts < MAX_SIMPLE_ATTEMPTS:
            log(f"[{wf_name}] Simple restart (attempt {attempts+1})")
            ok = restart_workflow(wf_id)
            ws["attempts"] = attempts + 1
            ws["last_action"] = "restart"
            state_changed = True

            if ok:
                time.sleep(5)
                execs2 = get_recent_executions(wf_id, limit=1)
                still_err = execs2 and execs2[0].get("status") in ("error", "crashed")
            else:
                still_err = True

            if not still_err:
                ws["status"] = "healthy"
                del state[wf_id]
                msg = f"✅ <b>{wf_name}</b> — 再起動で回復しました (試行{attempts+1}回目)"
                send_telegram(msg)
                messages.append(msg)
            else:
                msg = (
                    f"⚠️ <b>{wf_name}</b> — 再起動しましたが未回復 (試行{attempts+1}回目)\n"
                    f"ノード: <code>{node_name}</code> / エラー: <code>{err_msg[:150]}</code>"
                )
                send_telegram(msg)
                messages.append(f"⚠️ <b>{wf_name}</b> — 再起動中 (試行{attempts+1}回目)")

        # ── Attempt 3-4: LLM code fix ─────────────────────────────────────────
        elif attempts < MAX_LLM_ATTEMPTS:
            log(f"[{wf_name}] LLM fix attempt {attempts+1} — node={node_name}")
            node_info = get_node_code(wf_id, node_name)
            current_code = node_info.get("params", {}).get("jsCode", "")
            node_type = node_info.get("type", "")

            if "code" in node_type.lower() and current_code:
                send_telegram(
                    f"🤖 <b>{wf_name}</b> — ローカルLLMで修復を試みます (試行{attempts+1}回目)\n"
                    f"ノード: <code>{node_name}</code>\n"
                    f"エラー: <code>{err_msg[:150]}</code>"
                )

                fixed_code = llm_fix_js_code(node_name, current_code, err_msg)
                if fixed_code:
                    ok = apply_code_fix(wf_id, node_name, fixed_code)
                    if ok:
                        time.sleep(3)
                        restart_workflow(wf_id)
                        time.sleep(5)
                        execs2 = get_recent_executions(wf_id, limit=1)
                        still_err = execs2 and execs2[0].get("status") in ("error", "crashed")
                        if not still_err:
                            ws["status"] = "healthy"
                            del state[wf_id]
                            state_changed = True
                            msg = f"✅ <b>{wf_name}</b> — LLMによる自動修復成功！ (試行{attempts+1}回目)"
                            send_telegram(msg)
                            messages.append(msg)
                            continue
                        else:
                            send_telegram(
                                f"❌ <b>{wf_name}</b> — LLM修復コードを適用しましたが未回復")
                    else:
                        send_telegram(f"❌ <b>{wf_name}</b> — LLM修正コードの適用失敗")
                else:
                    send_telegram(f"❌ <b>{wf_name}</b> — LLMが修正コードを生成できませんでした")
            else:
                send_telegram(
                    f"⚠️ <b>{wf_name}</b> — Codeノード以外のエラー。LLM修復不可。\n"
                    f"ノード: <code>{node_name}</code> ({node_type})"
                )

            ws["attempts"] = attempts + 1
            ws["last_action"] = "llm_fix"
            state_changed = True
            messages.append(f"🤖 <b>{wf_name}</b> — LLM修復試行{attempts+1}回目")

    if state_changed:
        save_state(state)

    # Final summary if there are still failing workflows
    still_failing = [v for v in state.values() if v.get("status") != "healthy"]
    if still_failing:
        log(f"Still failing: {[v['name'] for v in still_failing]}")

    log("=== Workflow Healer done ===")
    return messages


if __name__ == "__main__":
    try:
        msgs = heal()
        if msgs:
            print("HEALER_MSGS:" + " | ".join(
                m.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                for m in msgs))
    except Exception as e:
        log(f"FATAL: {e}")
        send_telegram(f"🔥 workflow_healer.py クラッシュ: {e}")
        sys.exit(1)
