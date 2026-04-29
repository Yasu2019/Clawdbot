#!/usr/bin/env bash
set -euo pipefail
branch="ai-safe-change-$(date +%Y%m%d-%H%M%S)"
git status
git checkout -b "$branch"
git add -A
git commit -m "backup before AI-assisted OpenCode GO integration" || true
echo "Created backup branch: $branch"
