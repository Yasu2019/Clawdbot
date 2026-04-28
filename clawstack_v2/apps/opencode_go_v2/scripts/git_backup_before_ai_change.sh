#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
BRANCH="backup/before-ai-change-${STAMP}"
git status
git branch "$BRANCH"
echo "Created backup branch: $BRANCH"
