\
#!/usr/bin/env bash
set -euo pipefail

# Ollama + Copilot CLI local-offline launcher for Bash
# Usage:
#   bash ./run_copilot_local_offline.sh
# Change model below if needed.

export COPILOT_PROVIDER_BASE_URL="http://localhost:11434/v1"
export COPILOT_PROVIDER_API_KEY=
export COPILOT_PROVIDER_WIRE_API="responses"
export COPILOT_MODEL="qwen3.5"
export COPILOT_OFFLINE="true"

echo "Starting Copilot CLI with local Ollama in offline mode..."
copilot
