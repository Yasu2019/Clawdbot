#!/usr/bin/env bash
set -euo pipefail
TARGET_ROOT="${1:-/mnt/d/Clawdbot_Docker_20260125/ace_step_stack}"

for repo in \
  "$TARGET_ROOT/runtime/ComfyUI" \
  "$TARGET_ROOT/runtime/ComfyUI/custom_nodes/ACE-Step-ComfyUI"
do
  if [ -d "$repo/.git" ]; then
    echo "Updating $repo"
    git -C "$repo" pull --ff-only
  fi
done
