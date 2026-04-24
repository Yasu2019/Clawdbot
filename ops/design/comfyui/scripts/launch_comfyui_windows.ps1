Param(
  [string]$TargetRoot = "D:\Clawdbot_Docker_20260125\ace_step_stack",
  [int]$Port = 8188
)

$ErrorActionPreference = "Stop"
$wslCmd = @"
source /mnt/d/Clawdbot_Docker_20260125/ace_step_stack/runtime/.venv/bin/activate && \
python /mnt/d/Clawdbot_Docker_20260125/ace_step_stack/runtime/ComfyUI/main.py --listen 127.0.0.1 --port $Port
"@

wsl -d Ubuntu -- bash -lc $wslCmd
