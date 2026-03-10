"""
n8n AI Scout Workflow Creator
毎日、AI新モデル・ツールを検索してTelegramに通知するワークフローを作成する
"""
import json
import requests

N8N_URL = "http://localhost:5679"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

TELEGRAM_BOT_TOKEN = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"

# Search queries for AI Scout
SEARCH_QUERIES = [
    "new AI model small MiniPC 2026 release",
    "Qwen Llama Mistral new model release 2026",
    "video generation AI tool new release 2026",
    "image generation AI open source 2026",
    "AI productivity workflow automation tool 2026",
]

workflow = {
    "name": "Daily AI Scout (新AI・ツール探索)",
    "settings": {"executionOrder": "v1"},
    "nodes": [
        # 1. Schedule Trigger: 毎日09:00 JST (= 00:00 UTC)
        {
            "id": "node-schedule",
            "name": "Daily 09:00 JST",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 0],
            "parameters": {
                "rule": {
                    "interval": [{"field": "cronExpression", "expression": "0 0 * * *"}]
                }
            }
        },
        # 2. Set queries
        {
            "id": "node-queries",
            "name": "Search Queries",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [200, 0],
            "parameters": {
                "mode": "manual",
                "assignments": {
                    "assignments": [
                        {
                            "id": "q1",
                            "name": "q1",
                            "value": SEARCH_QUERIES[0],
                            "type": "string"
                        },
                        {
                            "id": "q2",
                            "name": "q2",
                            "value": SEARCH_QUERIES[1],
                            "type": "string"
                        },
                        {
                            "id": "q3",
                            "name": "q3",
                            "value": SEARCH_QUERIES[2],
                            "type": "string"
                        },
                        {
                            "id": "q4",
                            "name": "q4",
                            "value": SEARCH_QUERIES[3],
                            "type": "string"
                        },
                        {
                            "id": "q5",
                            "name": "q5",
                            "value": SEARCH_QUERIES[4],
                            "type": "string"
                        }
                    ]
                }
            }
        },
        # 3. Search 1
        {
            "id": "node-search1",
            "name": "Search: AI Models",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [420, -200],
            "parameters": {
                "method": "GET",
                "url": "http://searxng:8080/search",
                "sendQuery": True,
                "queryParameters": {
                    "parameters": [
                        {"name": "q", "value": "={{ $json.q1 }}"},
                        {"name": "format", "value": "json"},
                        {"name": "language", "value": "en"},
                        {"name": "time_range", "value": "week"}
                    ]
                }
            }
        },
        # 4. Search 2
        {
            "id": "node-search2",
            "name": "Search: LLM Releases",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [420, -80],
            "parameters": {
                "method": "GET",
                "url": "http://searxng:8080/search",
                "sendQuery": True,
                "queryParameters": {
                    "parameters": [
                        {"name": "q", "value": "={{ $json.q2 }}"},
                        {"name": "format", "value": "json"},
                        {"name": "language", "value": "en"},
                        {"name": "time_range", "value": "week"}
                    ]
                }
            }
        },
        # 5. Search 3
        {
            "id": "node-search3",
            "name": "Search: Video Gen AI",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [420, 40],
            "parameters": {
                "method": "GET",
                "url": "http://searxng:8080/search",
                "sendQuery": True,
                "queryParameters": {
                    "parameters": [
                        {"name": "q", "value": "={{ $json.q3 }}"},
                        {"name": "format", "value": "json"},
                        {"name": "language", "value": "en"},
                        {"name": "time_range", "value": "week"}
                    ]
                }
            }
        },
        # 6. Search 4
        {
            "id": "node-search4",
            "name": "Search: Image Gen AI",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [420, 160],
            "parameters": {
                "method": "GET",
                "url": "http://searxng:8080/search",
                "sendQuery": True,
                "queryParameters": {
                    "parameters": [
                        {"name": "q", "value": "={{ $json.q4 }}"},
                        {"name": "format", "value": "json"},
                        {"name": "language", "value": "en"},
                        {"name": "time_range", "value": "week"}
                    ]
                }
            }
        },
        # 7. Search 5
        {
            "id": "node-search5",
            "name": "Search: Productivity AI",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [420, 280],
            "parameters": {
                "method": "GET",
                "url": "http://searxng:8080/search",
                "sendQuery": True,
                "queryParameters": {
                    "parameters": [
                        {"name": "q", "value": "={{ $json.q5 }}"},
                        {"name": "format", "value": "json"},
                        {"name": "language", "value": "en"},
                        {"name": "time_range", "value": "week"}
                    ]
                }
            }
        },
        # 8. Code: Aggregate & format search results
        {
            "id": "node-aggregate",
            "name": "Aggregate Results",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [660, 40],
            "parameters": {
                "mode": "runOnceForAllItems",
                "jsCode": """
const allItems = $input.all();
const seen = new Set();
const results = [];

for (const item of allItems) {
  const data = item.json;
  const hits = data.results || [];
  for (const r of hits.slice(0, 3)) {
    const key = r.url || r.title;
    if (!seen.has(key) && r.title) {
      seen.add(key);
      results.push(`- ${r.title}\\n  ${r.url || ''}`);
    }
  }
}

return [{ json: { summary_input: results.slice(0, 20).join('\\n') } }];
"""
            }
        },
        # 9. LiteLLM (Gemini) - AI Summary
        {
            "id": "node-llm",
            "name": "Gemini Summary",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [880, 40],
            "parameters": {
                "method": "POST",
                "url": "http://litellm:4000/v1/chat/completions",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Authorization", "value": "Bearer local-dev-key"},
                        {"name": "Content-Type", "value": "application/json"}
                    ]
                },
                "sendBody": True,
                "contentType": "raw",
                "body": "={{ JSON.stringify({ model: 'google/gemini-2.5-flash', messages: [{ role: 'system', content: '鈴木さんのMiniPC（省電力・小型）に適合する新しいAIモデル・ツールをレポートしてください。特に: 小型LLM（Qwen/Llama等の軽量版）、動画生成AI、画像生成AI、仕事効率化ツール、に注目してください。日本語で簡潔に箇条書きで報告してください。既知のものは除外し、「新しい」ものだけを報告してください。' }, { role: 'user', content: '今週の検索結果:\\n' + $json.summary_input }], max_tokens: 800 }) }}"
            }
        },
        # 10. Extract LLM response
        {
            "id": "node-extract",
            "name": "Extract AI Report",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1100, 40],
            "parameters": {
                "jsCode": """
const body = $input.item.json;
const content = body.choices?.[0]?.message?.content || '(結果なし)';
const today = new Date().toLocaleDateString('ja-JP', {timeZone: 'Asia/Tokyo'});
return [{
  json: {
    message: `🤖 AI Scout 日報 (${today})\\n\\n${content}\\n\\n---\\n📡 Clawstack 自動探索`
  }
}];
"""
            }
        },
        # 11. Telegram notification
        {
            "id": "node-telegram",
            "name": "Telegram Notify",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1320, 40],
            "parameters": {
                "method": "POST",
                "url": f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                "sendBody": True,
                "contentType": "json",
                "body": {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": "={{ $json.message }}",
                    "parse_mode": "Markdown"
                }
            }
        }
    ],
    "connections": {
        "Daily 09:00 JST": {
            "main": [[{"node": "Search Queries", "type": "main", "index": 0}]]
        },
        "Search Queries": {
            "main": [[
                {"node": "Search: AI Models", "type": "main", "index": 0},
                {"node": "Search: LLM Releases", "type": "main", "index": 0},
                {"node": "Search: Video Gen AI", "type": "main", "index": 0},
                {"node": "Search: Image Gen AI", "type": "main", "index": 0},
                {"node": "Search: Productivity AI", "type": "main", "index": 0}
            ]]
        },
        "Search: AI Models": {
            "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
        },
        "Search: LLM Releases": {
            "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
        },
        "Search: Video Gen AI": {
            "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
        },
        "Search: Image Gen AI": {
            "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
        },
        "Search: Productivity AI": {
            "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
        },
        "Aggregate Results": {
            "main": [[{"node": "Gemini Summary", "type": "main", "index": 0}]]
        },
        "Gemini Summary": {
            "main": [[{"node": "Extract AI Report", "type": "main", "index": 0}]]
        },
        "Extract AI Report": {
            "main": [[{"node": "Telegram Notify", "type": "main", "index": 0}]]
        }
    }
}

resp = requests.post(
    f"{N8N_URL}/api/v1/workflows",
    headers=HEADERS,
    json=workflow
)
print("Status:", resp.status_code)
data = resp.json()
if resp.status_code in (200, 201):
    wf_id = data.get("id")
    print("Created workflow ID:", wf_id)
    print("Name:", data.get("name"))
    # Activate
    act = requests.patch(
        f"{N8N_URL}/api/v1/workflows/{wf_id}",
        headers=HEADERS,
        json={"active": True}
    )
    print("Activate status:", act.status_code)
else:
    print("Error:", json.dumps(data, indent=2, ensure_ascii=False))
