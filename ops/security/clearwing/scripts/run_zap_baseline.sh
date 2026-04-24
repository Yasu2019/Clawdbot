#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/configs/.env"

if [ ! -f "${ENV_FILE}" ]; then
  echo "[ERROR] configs/.env not found"
  exit 1
fi

TARGET_URL=$(grep '^TARGET_URL=' "${ENV_FILE}" | cut -d= -f2-)

if [[ -z "${TARGET_URL}" ]]; then
  echo "[ERROR] TARGET_URL is empty"
  exit 1
fi

mkdir -p "${ROOT_DIR}/reports"

echo "[WARN] Ensure TARGET_URL is an approved local/test target only."
docker run --rm -v "${ROOT_DIR}/reports:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable /bin/sh -lc "zap-baseline.py -t ${TARGET_URL} -r zap_report.html" || true

echo "[INFO] ZAP baseline finished. See reports/zap_report.html"
