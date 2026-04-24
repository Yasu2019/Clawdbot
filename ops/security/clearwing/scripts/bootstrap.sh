#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "${ROOT_DIR}/configs/.env" ]; then
  cp "${ROOT_DIR}/configs/.env.example" "${ROOT_DIR}/configs/.env"
  echo "[INFO] configs/.env を生成しました。必要に応じて編集してください。"
fi

mkdir -p "${ROOT_DIR}/reports"

echo "[INFO] Bootstrap completed."
echo "[INFO] Next:"
echo "  1) Edit configs/.env"
echo "  2) cd docker && docker compose --env-file ../configs/.env up -d"
