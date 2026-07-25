#!/bin/bash
# Clean environment setup (root)

# Ensure devices directory exists (do NOT wipe paired.json to preserve pairings across restarts)
mkdir -p /home/node/.openclaw/devices
[ -f /home/node/.openclaw/devices/paired.json ] || echo "{}" > /home/node/.openclaw/devices/paired.json
# Always reset pending (incomplete pairings are stale after restart)
echo "{}" > /home/node/.openclaw/devices/pending.json

# AUTO-UPDATE openclaw to latest on every startup
export PATH=$PATH:/usr/local/bin:/home/node/.npm-global/bin

NM_DIR="/usr/local/lib/node_modules"
OPENCLAW_DIR="$NM_DIR/openclaw"

# --- Step 0: Pre-update cleanup of stale npm rename artifacts ---------------
# npm's "rename swap" upgrade strategy can leave behind ".openclaw-XXXXXXXX"
# leftover directories if a previous update was interrupted (e.g. container
# killed mid-install). These stale dirs cause ENOTEMPTY on every subsequent
# `npm install -g openclaw@latest`, which previously created a crash loop.
# We do NOT blindly rm -rf here; instead we quarantine any leftover
# ".openclaw-*" dirs (other than the real "openclaw" dir) under node_modules
# itself (same overlay filesystem => mv is an instant rename, not a slow
# cross-filesystem copy through the Windows bind mount) so an operator can
# still inspect/recover them, then clear them from node_modules so npm's
# rename step has a clear target.
QUARANTINE_DIR="$NM_DIR/.entrypoint_quarantine"
mkdir -p "$QUARANTINE_DIR"
for stale in "$NM_DIR"/.openclaw-*; do
    [ -e "$stale" ] || continue
    ts=$(date +%Y%m%d_%H%M%S)
    base=$(basename "$stale")
    echo "[entrypoint] Found stale npm rename artifact: $stale — quarantining to $QUARANTINE_DIR/${base}_$ts"
    mv "$stale" "$QUARANTINE_DIR/${base}_$ts" 2>/dev/null || rm -rf "$stale" 2>/dev/null
done
# Keep only the most recent 3 quarantined entries to avoid unbounded growth.
ls -1dt "$QUARANTINE_DIR"/.openclaw-* 2>/dev/null | tail -n +4 | while IFS= read -r old; do
    rm -rf "$old" 2>/dev/null
done

# --- Step 1: Version pinning (auto-update DISABLED by policy) --------------
# INCIDENT HISTORY (2026-07-24/25): `npm install -g openclaw@latest` on every
# boot caused two compounding failures:
#   1. ENOTEMPTY crash loop — an interrupted npm rename left a stale
#      ".openclaw-XXXXXXXX" dir that blocked every subsequent install
#      (fixed by the Step 0 quarantine logic above).
#   2. Even after ENOTEMPTY was fixed, `openclaw@latest` resolved to
#      2026.7.1-2, whose package.json requires Node >=22.22.3, while this
#      image ships Node 22.22.1. The engine check makes openclaw.mjs exit
#      immediately, so the gateway process never starts and the container
#      crash-loops forever — no working version to roll back to, because
#      the incident began mid-update.
# DECISION: disable "always update to @latest" and instead pin to a known
# Node-22.22.1-compatible version. This is intentionally a manual-update
# policy (see PINNED_VERSION below) so a broken upstream release can never
# again prevent this container from booting. To adopt a newer openclaw,
# an operator must bump PINNED_VERSION here after confirming Node engine
# compatibility (`npm view openclaw@<version> engines`).
PINNED_VERSION="${OPENCLAW_PINNED_VERSION:-2026.6.33}"

CURRENT_NODE_VER=$(node --version 2>/dev/null | tr -d 'v')
INSTALLED_VER=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[0-9]+)?(-beta\.[0-9]+)?' | head -1)

echo "[entrypoint] Node runtime: $CURRENT_NODE_VER | openclaw installed: ${INSTALLED_VER:-none} | pinned target: $PINNED_VERSION"

# Snapshot the currently-installed openclaw dir before attempting any update,
# so we can roll back if the update produces a broken/incompatible install.
# IMPORTANT: this backup lives under $NM_DIR (same overlay filesystem as the
# real install), NOT under /home/node/.openclaw (a Windows bind mount) —
# copying ~300MB+ of node_modules through the bind mount was observed to hang
# in uninterruptible I/O wait (`cp` stuck in D state) and crash-loop the
# container. A local `cp -a` on the same filesystem is fast (seconds).
BACKUP_DIR=""
if [ -d "$OPENCLAW_DIR" ] && [ "$INSTALLED_VER" != "$PINNED_VERSION" ]; then
    BACKUP_DIR="$NM_DIR/.openclaw_backup_${INSTALLED_VER:-unknown}_$(date +%Y%m%d_%H%M%S)"
    if cp -a "$OPENCLAW_DIR" "$BACKUP_DIR" 2>/dev/null; then
        echo "[entrypoint] Backed up current openclaw ($INSTALLED_VER) to $BACKUP_DIR"
    else
        echo "[entrypoint] Warning: could not back up current openclaw before update"
        BACKUP_DIR=""
    fi
fi

if [ "$INSTALLED_VER" != "$PINNED_VERSION" ]; then
    echo "[entrypoint] Installing pinned openclaw@$PINNED_VERSION (current: ${INSTALLED_VER:-none})"
    if ! npm install -g "openclaw@$PINNED_VERSION" 2>&1 | tail -5; then
        echo "[entrypoint] WARNING: npm install -g openclaw@$PINNED_VERSION exited non-zero."
    fi
else
    echo "[entrypoint] openclaw $INSTALLED_VER already matches pinned version; skipping install."
fi

# --- Step 2: Post-update sanity check + auto-rollback -----------------------
# Failure modes handled here:
#   (a) npm install fails outright (ENOTEMPTY, network, registry errors)
#   (b) npm install "succeeds" but leaves /usr/local/bin/openclaw symlink
#       broken or pointing at a missing openclaw.mjs
#   (c) npm install succeeds but the resulting package.json "engines"
#       requirement is incompatible with the Node.js runtime in this image,
#       so `openclaw` exits immediately with an engine-check error and never
#       actually starts the gateway (this crash-loops the container).
# In every case, the container must still start with a WORKING openclaw
# rather than fail to boot. If the post-update binary is unusable and we
# have a backup of the previously-working version, roll back to it.
NEW_VERSION_WORKS=0
if [ -x /usr/local/bin/openclaw ] || command -v openclaw >/dev/null 2>&1; then
    if openclaw --version >/dev/null 2>&1; then
        NEW_VERSION_WORKS=1
    fi
fi

if [ "$NEW_VERSION_WORKS" -ne 1 ] && [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    echo "[entrypoint] New openclaw install is not runnable (update failed or Node engine mismatch)."
    echo "[entrypoint] Rolling back to previously-working openclaw from $BACKUP_DIR"
    rm -rf "$OPENCLAW_DIR" 2>/dev/null
    cp -a "$BACKUP_DIR" "$OPENCLAW_DIR" 2>/dev/null
    ln -sf ../lib/node_modules/openclaw/openclaw.mjs /usr/local/bin/openclaw 2>/dev/null
    chmod +x /usr/local/bin/openclaw 2>/dev/null
    if openclaw --version >/dev/null 2>&1; then
        echo "[entrypoint] Rollback successful — openclaw $(openclaw --version 2>/dev/null) is running."
    else
        echo "[entrypoint] ERROR: Rollback also failed to produce a runnable openclaw. Will continue boot; gateway command may fail."
    fi
elif [ "$NEW_VERSION_WORKS" -ne 1 ]; then
    echo "[entrypoint] ERROR: openclaw is not runnable and no backup is available to roll back to."
    echo "[entrypoint] Continuing boot anyway per fail-open policy; gateway command may fail."
fi

# Clean up old backup dirs under $NM_DIR, keep only the most recent 2.
ls -1dt "$NM_DIR"/.openclaw_backup_* 2>/dev/null | tail -n +3 | while IFS= read -r old; do
    rm -rf "$old" 2>/dev/null
done

# Ensure /usr/local/bin/openclaw symlink exists and points at a real file
# (defensive: some interrupted npm installs remove the symlink entirely).
if [ ! -e /usr/local/bin/openclaw ] && [ -f "$OPENCLAW_DIR/openclaw.mjs" ]; then
    echo "[entrypoint] Recreating missing /usr/local/bin/openclaw symlink."
    ln -sf ../lib/node_modules/openclaw/openclaw.mjs /usr/local/bin/openclaw 2>/dev/null
    chmod +x /usr/local/bin/openclaw 2>/dev/null
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
# Host-side paperless_rag_watchdog will restart it if it dies; this starts it on container boot
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

# Start inbox upload API (port 8099 — Portal inbox_uploader app)
nohup python3 /home/node/clawd/inbox_upload_api.py > /dev/null 2>&1 &
echo "[entrypoint] Inbox upload API started on port 8099 (PID $!)"

# Start RAG queue processor (rag_queue/ → Docling/PyMuPDF → Infinity embed → Qdrant)
nohup python3 /home/node/clawd/rag_queue_processor.py > /dev/null 2>&1 &
echo "[entrypoint] RAG queue processor started (PID $!)"

# Start inbox watcher (folder-drop → OpenClaw judgment → Telegram notification)
# Phase 1: observes OpenClaw judgment on dropped files; no automated actions yet
nohup python3 /home/node/clawd/inbox_watcher.py > /dev/null 2>&1 &
echo "[entrypoint] Inbox watcher started (PID $!)"

# Start the gateway with local proxy for Ollama (strips tools to fix 400 error)
node /home/node/.openclaw/ollama_proxy.js &

# Ensure we can run openclaw even if global install failed
if [[ "$1" == "openclaw" ]]; then
    shift
    if command -v openclaw &> /dev/null && openclaw --version >/dev/null 2>&1; then
        exec openclaw "$@"
    else
        echo "[entrypoint] WARNING: openclaw binary not found or not runnable. Using npx fallback."
        if npx -y openclaw --version >/dev/null 2>&1; then
            exec npx -y openclaw "$@"
        fi
        echo "[entrypoint] ERROR: openclaw is not runnable via binary or npx. Keeping container alive for diagnostics instead of exiting (fail-open policy)."
        echo "[entrypoint] Background services (ingest watchdog, MCP server, inbox APIs) remain running."
        exec tail -f /dev/null
    fi
fi

exec "$@"
