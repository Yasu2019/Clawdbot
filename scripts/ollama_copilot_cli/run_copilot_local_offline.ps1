\
# Ollama + Copilot CLI local-offline launcher for PowerShell
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\run_copilot_local_offline.ps1
# Change model below if needed.

$env:COPILOT_PROVIDER_BASE_URL="http://localhost:11434/v1"
$env:COPILOT_PROVIDER_API_KEY=""
$env:COPILOT_PROVIDER_WIRE_API="responses"
$env:COPILOT_MODEL="qwen3.5"
$env:COPILOT_OFFLINE="true"

Write-Host "Starting Copilot CLI with local Ollama in offline mode..."
copilot
