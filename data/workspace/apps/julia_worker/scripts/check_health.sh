#!/usr/bin/env bash
set -euo pipefail
echo "Julia Worker:"
curl -fsS http://localhost:8096/health
echo
echo "Python Bridge:"
curl -fsS http://localhost:8097/health
echo
