#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${KIMI_BASE_URL:-https://api.moonshot.ai/v1}"
if [[ -z "${MOONSHOT_API_KEY:-}" ]]; then
  echo "MOONSHOT_API_KEY is not set"
  exit 1
fi

status=$(curl -s -o /tmp/kimi_health.out -w "%{http_code}" \
  "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $MOONSHOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"kimi-k2.6","messages":[{"role":"user","content":"ping"}],"temperature":0.6}')

if [[ "$status" == "200" ]]; then
  echo "Kimi API OK"
else
  echo "Kimi API NG: HTTP $status"
  cat /tmp/kimi_health.out
  exit 1
fi
