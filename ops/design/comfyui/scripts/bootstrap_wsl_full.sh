#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT="${1:-/mnt/d/Clawdbot_Docker_20260125/ace_step_stack}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[ACE-Step] WSL bootstrap start: $TARGET_ROOT"

sudo apt-get update
sudo apt-get install -y git curl wget python3 python3-venv python3-pip ffmpeg build-essential

mkdir -p "$TARGET_ROOT"/{runtime,models,outputs,logs,portal_stub,configs}

if [ ! -f "$TARGET_ROOT/.env" ]; then
  cp "$ZIP_ROOT/configs/.env.example" "$TARGET_ROOT/.env"
fi

cp "$ZIP_ROOT/configs/docker-compose.ace-stack.yml" "$TARGET_ROOT/docker-compose.yml"
cp "$ZIP_ROOT/portal_stub/index.html" "$TARGET_ROOT/portal_stub/index.html"

if [ ! -d "$TARGET_ROOT/runtime/ComfyUI" ]; then
  git clone https://github.com/comfy-org/ComfyUI.git "$TARGET_ROOT/runtime/ComfyUI"
fi

python3 -m venv "$TARGET_ROOT/runtime/.venv"
source "$TARGET_ROOT/runtime/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$TARGET_ROOT/runtime/ComfyUI/requirements.txt"

mkdir -p "$TARGET_ROOT/runtime/ComfyUI/custom_nodes"
if [ ! -d "$TARGET_ROOT/runtime/ComfyUI/custom_nodes/ACE-Step-ComfyUI" ]; then
  git clone https://github.com/ace-step/ACE-Step-ComfyUI.git "$TARGET_ROOT/runtime/ComfyUI/custom_nodes/ACE-Step-ComfyUI"
fi

if [ -f "$TARGET_ROOT/runtime/ComfyUI/custom_nodes/ACE-Step-ComfyUI/requirements.txt" ]; then
  pip install -r "$TARGET_ROOT/runtime/ComfyUI/custom_nodes/ACE-Step-ComfyUI/requirements.txt"
fi

echo "[ACE-Step] WSL bootstrap complete"
echo "Next: source $TARGET_ROOT/runtime/.venv/bin/activate && python $TARGET_ROOT/runtime/ComfyUI/main.py --listen 127.0.0.1 --port 8188"
