#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
docker compose -f configs/docker-compose.hermes-openclaw.yml up -d --build
python3 scripts/healthcheck.py || true
