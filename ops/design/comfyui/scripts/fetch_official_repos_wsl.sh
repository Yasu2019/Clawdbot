#!/usr/bin/env bash
set -euo pipefail
TARGET_ROOT="${1:-/mnt/d/Clawdbot_Docker_20260125/ace_step_stack}"
mkdir -p "$TARGET_ROOT/sources"

if [ ! -d "$TARGET_ROOT/sources/ACE-Step-1.5" ]; then
  git clone https://github.com/ace-step/ACE-Step-1.5.git "$TARGET_ROOT/sources/ACE-Step-1.5"
fi

if [ ! -d "$TARGET_ROOT/sources/ComfyUI" ]; then
  git clone https://github.com/comfy-org/ComfyUI.git "$TARGET_ROOT/sources/ComfyUI"
fi

if [ ! -d "$TARGET_ROOT/sources/ACE-Step-ComfyUI" ]; then
  git clone https://github.com/ace-step/ACE-Step-ComfyUI.git "$TARGET_ROOT/sources/ACE-Step-ComfyUI"
fi

echo "Fetched official repositories into $TARGET_ROOT/sources"
