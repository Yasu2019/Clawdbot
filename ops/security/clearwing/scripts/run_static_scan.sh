#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${ROOT_DIR}/reports"

echo "[INFO] Running Semgrep..."
docker run --rm -v "${ROOT_DIR}:/src" semgrep/semgrep:latest semgrep --config auto /src > "${ROOT_DIR}/reports/semgrep.txt" || true

echo "[INFO] Running Bandit..."
docker run --rm -v "${ROOT_DIR}:/src" python:3.12-slim /bin/sh -lc "pip install --no-cache-dir bandit >/dev/null 2>&1 && bandit -r /src -f txt" > "${ROOT_DIR}/reports/bandit.txt" || true

echo "[INFO] Static scans finished. Reports in reports/"
