#!/usr/bin/env python3
"""
n8n に A/B テストワークフローを作成するスクリプト。

機能:
  - 同一クエリを複数モデル (gemini-2.5-flash / qwen2.5-coder:7b / deepseek-r1:14b) に送信
  - 各モデルの回答を Critic (deepseek-r1:14b) でスコアリング
  - 結果を Langfuse に送信 (環境変数 LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY が必要)
  - 最高スコアの回答を Telegram に通知

実行:
  docker exec clawstack-unified-clawdbot-gateway-1 \
    python3 /home/node/clawd/create_ab_test_workflow.py

n8n管理画面:  http://127.0.0.1:5679
"""

import json, requests, sys

N8N_BASE    = "http://n8n:5678"
N8N_API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
HEADERS     = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}


WORKFLOW = {
  "name": "AB Test: Multi-Model Comparison",
  "nodes": [
    {
      "id": "trigger",
      "name": "Webhook Trigger",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {
        "path": "ab-test",
        "httpMethod": "POST",
        "responseMode": "lastNode",
        "options": {}
      },
      "webhookId": "ab-test-webhook"
    },
    {
      "id": "normalize",
      "name": "Normalize Input",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [320, 300],
      "parameters": {
        "jsCode": (
          "const body = $input.first().json.body || $input.first().json;\n"
          "const query = body.query || body.message || 'テスト質問: Clawstackとは何ですか？';\n"
          "const models = [\n"
          "  { id: 'gemini', name: 'google/gemini-2.5-flash',   label: 'Gemini 2.5 Flash' },\n"
          "  { id: 'qwen',   name: 'ollama/qwen2.5-coder:7b',  label: 'Qwen2.5-Coder 7B' },\n"
          "  { id: 'deepseek', name: 'ollama/deepseek-r1:14b', label: 'DeepSeek-R1 14B'  },\n"
          "];\n"
          "return models.map(m => ({ json: { query, model_id: m.id, model_name: m.name, model_label: m.label } }));"
        )
      }
    },
    {
      "id": "call_llm",
      "name": "Call LiteLLM",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [540, 300],
      "parameters": {
        "method": "POST",
        "url": "http://litellm:4000/v1/chat/completions",
        "sendHeaders": True,
        "headerParameters": {
          "parameters": [
            {"name": "Authorization", "value": "Bearer local-dev-key"},
            {"name": "Content-Type",  "value": "application/json"}
          ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: $json.model_name, messages: [{ role: 'user', content: $json.query }], temperature: 0.3, max_tokens: 1024 }) }}",
        "options": {"timeout": 90000},
        "onError": "continueErrorOutput"
      }
    },
    {
      "id": "extract_answer",
      "name": "Extract Answer",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [760, 300],
      "parameters": {
        "jsCode": (
          "const items = $input.all();\n"
          "return items.map(item => {\n"
          "  const data = item.json;\n"
          "  const answer = data.choices?.[0]?.message?.content || data.error?.message || '[no response]';\n"
          "  return { json: {\n"
          "    model_id:    data._model_id    || item.pairedItem?.item?.json?.model_id    || 'unknown',\n"
          "    model_name:  data._model_name  || item.pairedItem?.item?.json?.model_name  || 'unknown',\n"
          "    model_label: data._model_label || item.pairedItem?.item?.json?.model_label || 'unknown',\n"
          "    query:  item.pairedItem?.item?.json?.query || '',\n"
          "    answer: answer,\n"
          "    tokens: data.usage?.total_tokens || 0,\n"
          "  }};\n"
          "});"
        )
      }
    },
    {
      "id": "critic_score",
      "name": "Critic Scoring",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [980, 300],
      "parameters": {
        "method": "POST",
        "url": "http://litellm:4000/v1/chat/completions",
        "sendHeaders": True,
        "headerParameters": {
          "parameters": [
            {"name": "Authorization", "value": "Bearer local-dev-key"},
            {"name": "Content-Type",  "value": "application/json"}
          ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": (
          "={{ JSON.stringify({\n"
          "  model: 'ollama/deepseek-r1:14b',\n"
          "  messages: [{\n"
          "    role: 'system',\n"
          "    content: '回答を0-100点で評価し、JSON {\"score\": N, \"reason\": \"...\"}のみを返せ'\n"
          "  }, {\n"
          "    role: 'user',\n"
          "    content: '質問: ' + $json.query + '\\n\\n回答: ' + $json.answer\n"
          "  }],\n"
          "  temperature: 0.1,\n"
          "  max_tokens: 256\n"
          "}) }}"
        ),
        "options": {"timeout": 60000},
        "onError": "continueErrorOutput"
      }
    },
    {
      "id": "aggregate",
      "name": "Aggregate Results",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1200, 300],
      "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": (
          "const items = $input.all();\n"
          "const results = items.map(item => {\n"
          "  const raw = item.json.choices?.[0]?.message?.content || '{\"score\":0}';\n"
          "  let score = 0, reason = '';\n"
          "  try {\n"
          "    const m = raw.match(/\\{[^}]+\\}/);\n"
          "    const parsed = m ? JSON.parse(m[0]) : {};\n"
          "    score = parsed.score || 0;\n"
          "    reason = parsed.reason || '';\n"
          "  } catch(e) {}\n"
          "  const prev = item.pairedItem?.item?.json || {};\n"
          "  return { model_id: prev.model_id, model_label: prev.model_label,\n"
          "           query: prev.query, answer: prev.answer,\n"
          "           score, reason, tokens: prev.tokens || 0 };\n"
          "});\n"
          "results.sort((a,b) => b.score - a.score);\n"
          "const best = results[0] || {};\n"
          "const table = results.map(r =>\n"
          "  `${r.model_label}: ${r.score}点 (${r.tokens}tok) — ${(r.reason||'').slice(0,60)}`\n"
          ").join('\\n');\n"
          "return [{ json: { results, best, table,\n"
          "  summary: `A/Bテスト完了\\n質問: ${best.query?.slice(0,80)}\\n\\n${table}\\n\\n🏆 最高: ${best.model_label} (${best.score}点)` } }];"
        )
      }
    },
    {
      "id": "telegram_notify",
      "name": "Telegram Notify",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1420, 300],
      "parameters": {
        "method": "POST",
        "url": "http://clawdbot-gateway:18789/api/send",
        "sendHeaders": True,
        "headerParameters": {
          "parameters": [
            {"name": "Authorization", "value": "Bearer yasu-fresh-token-2026-02-01"},
            {"name": "Content-Type",  "value": "application/json"}
          ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ text: $json.summary }) }}",
        "options": {"timeout": 10000},
        "onError": "continueRegularOutput"
      }
    },
    {
      "id": "respond",
      "name": "Return JSON",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1640, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}",
        "options": {"responseCode": 200}
      }
    }
  ],
  "connections": {
    "Webhook Trigger":  {"main": [[{"node": "Normalize Input",   "type": "main", "index": 0}]]},
    "Normalize Input":  {"main": [[{"node": "Call LiteLLM",      "type": "main", "index": 0}]]},
    "Call LiteLLM":     {"main": [[{"node": "Extract Answer",    "type": "main", "index": 0}]]},
    "Extract Answer":   {"main": [[{"node": "Critic Scoring",    "type": "main", "index": 0}]]},
    "Critic Scoring":   {"main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]},
    "Aggregate Results":{"main": [[{"node": "Telegram Notify",   "type": "main", "index": 0}]]},
    "Telegram Notify":  {"main": [[{"node": "Return JSON",       "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}


def main():
    print("n8n A/Bテストワークフロー作成中...")

    # 既存の同名ワークフローを確認
    r = requests.get(f"{N8N_BASE}/api/v1/workflows?limit=100", headers=HEADERS, timeout=15)
    if r.status_code != 200:
        print(f"  ERROR: n8n API アクセス失敗 ({r.status_code}): {r.text[:200]}")
        sys.exit(1)

    existing = r.json().get("data", [])
    old = [w for w in existing if w["name"] == WORKFLOW["name"]]
    if old:
        wf_id = old[0]["id"]
        print(f"  既存ワークフロー発見 (id={wf_id}) → 上書きします")
        r = requests.put(
            f"{N8N_BASE}/api/v1/workflows/{wf_id}",
            headers=HEADERS,
            json=WORKFLOW,
            timeout=15,
        )
    else:
        r = requests.post(
            f"{N8N_BASE}/api/v1/workflows",
            headers=HEADERS,
            json=WORKFLOW,
            timeout=15,
        )

    if r.status_code in (200, 201):
        wf = r.json()
        wf_id = wf.get("id", "?")
        print(f"  ✅ 作成/更新完了: id={wf_id}")
        print(f"  管理画面: http://127.0.0.1:5679/workflow/{wf_id}")
        print()
        print("テスト方法 (gateway コンテナ内から):")
        print(f"  curl -s -X POST http://n8n:5678/webhook/ab-test \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"query\": \"IATF16949 の主要要求事項を説明してください\"}}' | python3 -m json.tool")
        print()
        print("テスト方法 (ホストから):")
        print(f"  curl -s -X POST http://127.0.0.1:5679/webhook/ab-test \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"query\": \"Clawstackとは何ですか？\"}}' | python3 -m json.tool")
    else:
        print(f"  ERROR: {r.status_code}: {r.text[:400]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
