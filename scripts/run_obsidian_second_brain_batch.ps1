$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python data\workspace\obsidian_vault_manager.py second-brain-batch `
  --include-path 30_AI_DevOps `
  --limit 20 `
  --batch-name ai_devops `
  --dry-run
