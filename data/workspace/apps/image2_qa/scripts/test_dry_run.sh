#!/usr/bin/env bash
set -euo pipefail
curl -sS -X POST http://127.0.0.1:18789/api/image2-qa/generate \
  -H 'Content-Type: application/json; charset=utf-8' \
  --data-binary @samples/request_internal_audit.json | jq .
