#!/usr/bin/env bash
set -euo pipefail

echo "OpenClaw Vision Quality Inspection setup"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env を作成しました"
fi

docker compose -f docker-compose.vision.yml up -d --build

echo "起動しました"
echo "UI:  http://localhost:8095"
echo "API: http://localhost:18795/health"
