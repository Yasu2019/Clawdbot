#!/usr/bin/env bash
set -euo pipefail
stamp=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
tar --exclude='backups' -czf "backups/hermes_workspace_${stamp}.tar.gz" workspace 2>/dev/null || true
echo "backup created: backups/hermes_workspace_${stamp}.tar.gz"
