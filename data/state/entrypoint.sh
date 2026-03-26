#!/bin/bash
# Clean environment setup (root)

# Ensure devices directory exists (do NOT wipe paired.json to preserve pairings across restarts)
mkdir -p /home/node/.openclaw/devices
[ -f /home/node/.openclaw/devices/paired.json ] || echo "{}" > /home/node/.openclaw/devices/paired.json
# Always reset pending (incomplete pairings are stale after restart)
echo "{}" > /home/node/.openclaw/devices/pending.json

# FORCING REINSTALLATION IF MISSING
export PATH=$PATH:/usr/local/bin:/home/node/.npm-global/bin
if ! command -v openclaw &> /dev/null; then
    echo "[entrypoint] openclaw not found. Attempting installation..."
    npm install -g openclaw
fi

# Wrapper function for openclaw to handle both binary and npx
openclaw() {
    if command -v openclaw &> /dev/null && [ "$(command -v openclaw)" != "openclaw" ]; then
        command openclaw "$@"
    else
        npx -y openclaw "$@"
    fi
}
export -f openclaw

# Install Chromium shared library dependencies if not already present
# Required for Playwright Chromium (headless browser for agent)
if ! ldconfig -p 2>/dev/null | grep -q libatk-bridge; then
    echo "[entrypoint] Installing Chromium runtime dependencies..."
    apt-get update -qq 2>/dev/null && \
    apt-get install -y -qq --no-install-recommends \
        libatk-bridge2.0-0 libgtk-3-0 libgbm1 libxss1 libasound2 libx11-xcb1 \
        2>/dev/null && \
    echo "[entrypoint] Chromium dependencies installed." || \
    echo "[entrypoint] Warning: Could not install Chromium dependencies."
else
    echo "[entrypoint] Chromium dependencies already present."
fi

# Auto-approve pending device pairing requests from trusted IPs (Control UI reconnect)
chmod +x /home/node/.openclaw/auto_approve.sh
/home/node/.openclaw/auto_approve.sh &

# Install Python packages for email RAG pipeline (Phase 2 attachments)
pip3 install --quiet --break-system-packages openpyxl xlrd python-docx 2>/dev/null || true

# Start ingest watchdog (Paperless API → Qdrant universal_knowledge)
# n8n supervisor will restart it every 5 min if it dies; this starts it on container boot
if python3 -c "import fitz, requests" 2>/dev/null; then
    nohup python3 /home/node/clawd/ingest_watchdog.py >> /home/node/clawd/ingest_watchdog.log 2>&1 &
    echo "[entrypoint] Ingest watchdog started (PID $!)"
else
    echo "[entrypoint] Warning: PyMuPDF or requests not available — ingest watchdog not started"
fi

# Start Clawstack MCP server (Qdrant RAG search + SearXNG web search tools)
# Listens on 127.0.0.1:9876/mcp — registered in .claude.json as "clawstack-tools"
if ! python3 -c "import mcp" 2>/dev/null; then
    echo "[entrypoint] Installing mcp and langfuse Python packages..."
    pip3 install --quiet --break-system-packages "mcp[cli]>=1.6.0" langfuse 2>&1 | tail -3
fi
if python3 -c "import mcp, requests" 2>/dev/null; then
    nohup python3 /home/node/clawd/clawstack_mcp_server.py >> /home/node/clawd/clawstack_mcp.log 2>&1 &
    echo "[entrypoint] Clawstack MCP server started (PID $!)"
else
    echo "[entrypoint] Warning: mcp or requests not available — clawstack MCP server not started"
fi

# Start summary cache builder (generates LLM summaries for email tasks in background)
# Pauses when Ollama is busy, resumes when idle — no API consumption
nohup python3 /home/node/clawd/summary_cache_builder.py >> /home/node/clawd/summary_cache_builder.log 2>&1 &
echo "[entrypoint] Summary cache builder started (PID $!)"

# Start the gateway with local proxy for Ollama (strips tools to fix 400 error)
node /home/node/.openclaw/ollama_proxy.js &

# Ensure we can run openclaw even if global install failed
if [[ "$1" == "openclaw" ]]; then
    shift
    if command -v openclaw &> /dev/null; then
        exec openclaw "$@"
    else
        echo "[entrypoint] WARNING: openclaw binary not found. Using npx fallback."
        exec npx -y openclaw "$@"
    fi
fi

exec "$@"
