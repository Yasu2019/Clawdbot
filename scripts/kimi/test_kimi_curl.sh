#!/usr/bin/env bash
set -euo pipefail

: "${MOONSHOT_API_KEY:?MOONSHOT_API_KEY is required}"
BASE_URL="${KIMI_BASE_URL:-https://api.moonshot.ai/v1}"
MODEL="${KIMI_MODEL_PRIMARY:-kimi-k2.6}"

curl -sS "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $MOONSHOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<JSON
{
  "model": "$MODEL",
  "temperature": 0.6,
  "messages": [
    {"role": "system", "content": "You are a concise QA assistant."},
    {"role": "user", "content": "品質異常の一次報告テンプレートを日本語で作成してください。"}
  ]
}
JSON
