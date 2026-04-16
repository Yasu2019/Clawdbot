#!/usr/bin/env bash
set -euo pipefail

echo "[1] stop services"
docker compose down || true

echo "[2] show git diff"
git diff || true

echo "[3] restore tracked files"
git restore . || true

echo "[4] restart services"
docker compose up -d || true

echo "rollback procedure finished"
