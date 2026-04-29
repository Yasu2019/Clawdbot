#!/usr/bin/env bash
set -euo pipefail

echo "Step 1: Git backup"
bash scripts/git_safe_backup.sh

echo "Step 2: Standalone build and start"
docker compose -f docker-compose.julia-worker.standalone.yml up -d --build

echo "Step 3: Health check"
sleep 5
curl -fsS http://localhost:8096/health
echo
curl -fsS http://localhost:8097/health
echo

echo "Julia Numerical Worker standalone start completed."
