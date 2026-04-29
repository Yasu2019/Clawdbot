#!/usr/bin/env bash
set -euo pipefail
curl -s http://localhost:18081/health | jq .
curl -s -X POST http://localhost:18081/tts/speak \
  -H 'Content-Type: application/json' \
  -d '{"text":"品質保証部からのお知らせです。","purpose":"factory_alert"}' | jq .
