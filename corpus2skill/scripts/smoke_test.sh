#!/usr/bin/env bash
set -e
for port in 18920 18921 18922 18923; do
  echo "checking $port"
  curl -fsS "http://127.0.0.1:${port}/health" || true
  echo
 done
