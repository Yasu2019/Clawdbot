#!/usr/bin/env python3
"""
n8n ワークフロー一括再作成スクリプト (DB リセット後復旧用)
コンテナ内から実行:
  python3 /home/node/clawd/recreate_workflows.py

対象:
  1. RLAnything Phase2 Monitor    (毎時 0分)
  2. P017 Workflow Self-Healer    (15分毎)
  3. Ingest Watchdog Supervisor   (5分毎)
  4. AB Test: Multi-Model Comparison (webhook)
"""

import sys, json, http.cookiejar
from pathlib import Path
import urllib.request, urllib.error

WORKSPACE = Path(__file__).resolve().parent
BASE   = "http://n8n:5678" if Path("/home/node/clawd").exists() else "http://127.0.0.1:5679"
EMAIL  = "y.suzuki.hk@gmail.com"
PASSWD = "Foxconnjpn75"
EXEC_CMD_PATTERN = (
    "DOCKER_HOST=unix:///var/run/docker.sock "
    "docker exec clawstack-unified-clawdbot-gateway-1 "
    "python3 /home/node/clawd/{script} 2>&1 | tail -60"
)

# ─── Auth ───────────────────────────────────────────────────────────────────
_token = None

def get_token() -> str:
    global _token
    if _token:
        return _token
    req = urllib.request.Request(
        BASE + "/rest/login",
        data=json.dumps({"emailOrLdapLoginId": EMAIL, "password": PASSWD}).encode(),
        headers={"Content-Type": "application/json", "browser-id": "clawstack001"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        for hdr in r.headers.get_all("Set-Cookie") or []:
            if "n8n-auth=" in hdr:
                _token = hdr.split("n8n-auth=")[1].split(";")[0]
                return _token
    raise RuntimeError("n8n ログイン失敗：n8n-auth Cookie が見つかりません")

def api(method: str, path: str, body=None) -> dict:
    token = get_token()
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={
            "Content-Type": "application/json",
            "Cookie": f"n8n-auth={token}",
            "browser-id": "clawstack001",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body_b = e.read()
        try:
            return e.code, json.loads(body_b)
        except Exception:
            return e.code, {"raw": body_b.decode(errors="replace")[:200]}

def create_or_update(workflow: dict) -> str:
    """ワークフロー作成または更新。ワークフローIDを返す。"""
    st, wfs = api("GET", "/rest/workflows?limit=100")
    existing = [w for w in wfs.get("data", []) if w.get("name") == workflow["name"]]

    if existing:
        wf_id = existing[0]["id"]
        st, result = api("PUT", f"/rest/workflows/{wf_id}", workflow)
        action = "更新"
        if st == 404:
            result = {"data": {"id": wf_id}}
            action = "既存維持"
    else:
        st, result = api("POST", "/rest/workflows", workflow)
        wf_id = result.get("data", result).get("id", "?")
        action = "新規作成"

    if st == 404 and existing:
        wf_id = existing[0]["id"]
        print(f"  [{action}] id={wf_id}")
        return wf_id

    if st not in (200, 201):
        print(f"  ERROR ({st}): {str(result)[:200]}")
        return ""

    wf_id = result.get("data", result).get("id", wf_id)
    print(f"  [{action}] id={wf_id}")
    return wf_id

def set_active_state(wf_id: str, should_be_active: bool) -> bool:
    st, wf = api("GET", f"/rest/workflows/{wf_id}")
    ver = wf.get("data", wf).get("versionId", "")
    if should_be_active:
        st2, res = api("POST", f"/rest/workflows/{wf_id}/activate", {"versionId": ver})
    else:
        st2, res = api("POST", f"/rest/workflows/{wf_id}/deactivate", {})
    active = res.get("data", res).get("active", False)
    print(f"  active={active}")
    return active

# ─── Workflow Definitions ─────────────────────────────────────────────────────

def exec_node(nid, name, script, pos):
    return {
        "id": nid, "name": name,
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": pos,
        "parameters": {"command": EXEC_CMD_PATTERN.format(script=script)},
    }

def schedule_node(nid, name, cron, pos):
    return {
        "id": nid, "name": name,
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": pos,
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}},
    }

PHASE2_MONITOR = {
    "name": "RLAnything Phase2 Monitor",
    "active": True,
    "nodes": [
        schedule_node("sched", "Schedule: 毎時0分", "0 * * * *", [250, 300]),
        exec_node("exec", "Run score_calculator.py",
                  "rl_anything/score_calculator.py", [500, 300]),
        {"id": "noop", "name": "Log", "type": "n8n-nodes-base.noOp",
         "typeVersion": 1, "position": [750, 300], "parameters": {}},
    ],
    "connections": {
        "Schedule: 毎時0分":        {"main": [[{"node": "Run score_calculator.py", "type": "main", "index": 0}]]},
        "Run score_calculator.py": {"main": [[{"node": "Log", "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
}

SELF_HEALER = {
    "name": "P017 Workflow Self-Healer",
    "active": True,
    "nodes": [
        schedule_node("sched", "Schedule: 15分毎", "*/15 * * * *", [250, 300]),
        exec_node("exec", "Run workflow_healer.py",
                  "workflow_healer.py", [500, 300]),
        {"id": "noop", "name": "Log", "type": "n8n-nodes-base.noOp",
         "typeVersion": 1, "position": [750, 300], "parameters": {}},
    ],
    "connections": {
        "Schedule: 15分毎":       {"main": [[{"node": "Run workflow_healer.py", "type": "main", "index": 0}]]},
        "Run workflow_healer.py": {"main": [[{"node": "Log", "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
}

INGEST_WATCHDOG = {
    "name": "Ingest Watchdog Supervisor",
    "active": False,
    "nodes": [
        schedule_node("sched", "Schedule: 5分毎", "*/5 * * * *", [250, 300]),
        {
            "id": "exec",
            "name": "Log ownership handoff",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [500, 300],
            "parameters": {
                "command": (
                    "echo 'disabled: host-side paperless_rag_watchdog owns ingest_watchdog lifecycle'"
                )
            },
        },
        {"id": "noop", "name": "Log", "type": "n8n-nodes-base.noOp",
         "typeVersion": 1, "position": [750, 300], "parameters": {}},
    ],
    "connections": {
        "Schedule: 5分毎":          {"main": [[{"node": "Log ownership handoff", "type": "main", "index": 0}]]},
        "Log ownership handoff":    {"main": [[{"node": "Log", "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
}

AB_TEST = {
    "name": "AB Test: Multi-Model Comparison",
    "active": True,
    "nodes": [
        {
            "id": "trigger", "name": "Webhook Trigger",
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [100, 300],
            "parameters": {
                "path": "ab-test", "httpMethod": "POST",
                "responseMode": "lastNode", "options": {},
            },
            "webhookId": "ab-test-webhook",
        },
        {
            "id": "normalize", "name": "Normalize Input",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [320, 300],
            "parameters": {
                "jsCode": (
                    "const body = $input.first().json.body || $input.first().json;\n"
                    "const query = body.query || body.message || 'Clawstackとは何ですか？';\n"
                    "const models = [\n"
                    "  { id: 'gemini',   name: 'google/gemini-2.5-flash',  label: 'Gemini 2.5 Flash' },\n"
                    "  { id: 'qwen',     name: 'ollama/qwen2.5-coder:7b', label: 'Qwen2.5-Coder 7B' },\n"
                    "  { id: 'deepseek', name: 'ollama/deepseek-r1:14b',  label: 'DeepSeek-R1 14B'  },\n"
                    "];\n"
                    "return models.map(m => ({ json: { query, model_id: m.id, model_name: m.name, model_label: m.label } }));"
                )
            },
        },
        {
            "id": "call_llm", "name": "Call LiteLLM",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [540, 300],
            "parameters": {
                "method": "POST",
                "url": "http://litellm:4000/v1/chat/completions",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": "Bearer local-dev-key"},
                    {"name": "Content-Type",  "value": "application/json"},
                ]},
                "sendBody": True, "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({ model: $json.model_name, messages: [{ role: 'user', content: $json.query }], temperature: 0.3, max_tokens: 1024 }) }}",
                "options": {"timeout": 90000},
                "onError": "continueErrorOutput",
            },
        },
        {
            "id": "extract_answer", "name": "Extract Answer",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [760, 300],
            "parameters": {
                "jsCode": (
                    "const items = $input.all();\n"
                    "return items.map(item => {\n"
                    "  const data = item.json;\n"
                    "  const answer = data.choices?.[0]?.message?.content || data.error?.message || '[no response]';\n"
                    "  return { json: {\n"
                    "    model_id:    item.pairedItem?.item?.json?.model_id    || 'unknown',\n"
                    "    model_name:  item.pairedItem?.item?.json?.model_name  || 'unknown',\n"
                    "    model_label: item.pairedItem?.item?.json?.model_label || 'unknown',\n"
                    "    query:  item.pairedItem?.item?.json?.query || '',\n"
                    "    answer: answer,\n"
                    "    tokens: data.usage?.total_tokens || 0,\n"
                    "  }};\n"
                    "});"
                )
            },
        },
        {
            "id": "critic_score", "name": "Critic Scoring",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [980, 300],
            "parameters": {
                "method": "POST",
                "url": "http://litellm:4000/v1/chat/completions",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": "Bearer local-dev-key"},
                    {"name": "Content-Type",  "value": "application/json"},
                ]},
                "sendBody": True, "specifyBody": "json",
                "jsonBody": (
                    '={{ JSON.stringify({ model: "ollama/deepseek-r1:14b", messages: ['
                    '{ role: "system", content: "回答を0-100点で評価し、JSON {score: N, reason: ...}のみを返せ" },'
                    '{ role: "user", content: "質問: " + $json.query + "\\n\\n回答: " + $json.answer }'
                    '], temperature: 0.1, max_tokens: 256 }) }}'
                ),
                "options": {"timeout": 60000},
                "onError": "continueErrorOutput",
            },
        },
        {
            "id": "aggregate", "name": "Aggregate Results",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1200, 300],
            "parameters": {
                "mode": "runOnceForAllItems",
                "jsCode": (
                    "const items = $input.all();\n"
                    "const results = items.map(item => {\n"
                    "  const raw = item.json.choices?.[0]?.message?.content || '{\"score\":0}';\n"
                    "  let score = 0, reason = '';\n"
                    "  try { const m = raw.match(/\\{[^}]+\\}/); const p = m ? JSON.parse(m[0]) : {}; score = p.score||0; reason = p.reason||''; } catch(e) {}\n"
                    "  const prev = item.pairedItem?.item?.json || {};\n"
                    "  return { model_id: prev.model_id, model_label: prev.model_label,\n"
                    "           query: prev.query, answer: prev.answer, score, reason, tokens: prev.tokens||0 };\n"
                    "});\n"
                    "results.sort((a,b) => b.score - a.score);\n"
                    "const best = results[0] || {};\n"
                    "const table = results.map(r => `${r.model_label}: ${r.score}点 (${r.tokens}tok) — ${(r.reason||'').slice(0,60)}`).join('\\n');\n"
                    "return [{ json: { results, best, table,\n"
                    "  summary: `A/Bテスト完了\\n質問: ${(best.query||'').slice(0,80)}\\n\\n${table}\\n\\n最高: ${best.model_label} (${best.score}点)` } }];"
                ),
            },
        },
        {
            "id": "telegram_notify", "name": "Telegram Notify",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [1420, 300],
            "parameters": {
                "method": "POST",
                "url": "http://clawdbot-gateway:18789/api/send",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "Authorization", "value": "Bearer yasu-fresh-token-2026-02-01"},
                    {"name": "Content-Type",  "value": "application/json"},
                ]},
                "sendBody": True, "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify({ text: $json.summary }) }}",
                "options": {"timeout": 10000},
                "onError": "continueRegularOutput",
            },
        },
        {
            "id": "respond", "name": "Return JSON",
            "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
            "position": [1640, 300],
            "parameters": {
                "respondWith": "json",
                "responseBody": "={{ $json }}",
                "options": {"responseCode": 200},
            },
        },
    ],
    "connections": {
        "Webhook Trigger":  {"main": [[{"node": "Normalize Input",   "type": "main", "index": 0}]]},
        "Normalize Input":  {"main": [[{"node": "Call LiteLLM",      "type": "main", "index": 0}]]},
        "Call LiteLLM":     {"main": [[{"node": "Extract Answer",    "type": "main", "index": 0}]]},
        "Extract Answer":   {"main": [[{"node": "Critic Scoring",    "type": "main", "index": 0}]]},
        "Critic Scoring":   {"main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]},
        "Aggregate Results":{"main": [[{"node": "Telegram Notify",   "type": "main", "index": 0}]]},
        "Telegram Notify":  {"main": [[{"node": "Return JSON",       "type": "main", "index": 0}]]},
    },
    "settings": {"executionOrder": "v1"},
}

# ─── Main ─────────────────────────────────────────────────────────────────────

WORKFLOWS = [
    ("Phase2 Monitor",        PHASE2_MONITOR),
    ("P017 Self-Healer",      SELF_HEALER),
    ("Ingest Watchdog",       INGEST_WATCHDOG),
    ("AB Test Multi-Model",   AB_TEST),
]

results = {}
print("=" * 60)
print("n8n ワークフロー一括再作成")
print("=" * 60)

for label, wf_def in WORKFLOWS:
    print(f"\n[{label}]")
    wf_id = create_or_update(wf_def)
    if wf_id:
        ok = set_active_state(wf_id, bool(wf_def.get("active", True)))
        results[label] = {"id": wf_id, "active": ok}
    else:
        results[label] = {"id": None, "active": False}

print("\n" + "=" * 60)
print("完了サマリー")
print("=" * 60)
for label, r in results.items():
    status = "OK" if r["active"] else "NG"
    print(f"  [{status}] {label:30s}  id={r['id']}")

print()
print("A/B Test webhook URL:")
ab_id = results.get("AB Test Multi-Model", {}).get("id", "?")
print(f"  http://127.0.0.1:5679/webhook/ab-test  (POST)")
print(f"  n8n管理: http://127.0.0.1:5679/workflow/{ab_id}")
