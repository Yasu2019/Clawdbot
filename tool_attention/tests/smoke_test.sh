#!/usr/bin/env bash
set -e
curl -s http://localhost:8092/ranking || true
curl -s -X POST http://localhost:8090/route -H 'Content-Type: application/json' -d '{"text":"SQLで不良率を確認","state":{"db_connected":true},"limit":5}' | jq .
