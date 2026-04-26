#!/usr/bin/env bash
set -e

echo "Checking protected file changes..."
files=$(git diff --name-only || true)
if echo "$files" | grep -E "app/views/layouts|app/views/shared|app/assets|app/javascript|config/routes.rb|\.env|config/master.key|config/credentials.yml.enc"; then
  echo "ERROR: Protected files modified. Create GitHub backup and confirm explicit approval before proceeding."
  exit 1
fi

echo "Guardrails OK"
