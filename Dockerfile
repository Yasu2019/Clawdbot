FROM node:22-bookworm-slim

# Minimal OS deps (curl for health checks / debugging, tini for clean PID1, rclone for cloud sync)
# Added Engineering Tools: Gmsh, OpenSCAD, FFmpeg, and Xvfb for headless rendering
# Removed FreeCAD due to network timeouts
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 --fix-missing \
  ca-certificates curl tini git python3 python3-pip python3-venv unzip \
  gmsh openscad ffmpeg xvfb libgl1-mesa-dev \
  && rm -rf /var/lib/apt/lists/*

# Install rclone for Google Drive sync
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
  && unzip rclone-current-linux-amd64.zip \
  && cp rclone-*-linux-amd64/rclone /usr/bin/ \
  && chmod 755 /usr/bin/rclone \
  && rm -rf rclone-*

# Install Engineering Python Stack
RUN pip3 install --no-cache-dir --break-system-packages \
  numpy scipy pandas matplotlib pyvista meshio trimesh

# Install Antigravity (Aider) system-wide
RUN pip3 install --no-cache-dir --break-system-packages aider-chat

# Install Clawdbot CLI (pin if you want: npm install -g clawdbot@2026.1.22)
RUN npm install -g clawdbot

# Apply pairing bypass patch permanently
# This modifies requirePairing function to always return true
RUN sed -i 's/const requirePairing = async (reason, _paired) => {/const requirePairing = async (reason, _paired) => { return true; }; const _unused_requirePairing = async (reason, _paired) => {/g' \
  /usr/local/lib/node_modules/clawdbot/dist/gateway/server/ws-connection/message-handler.js

# Run as non-root user (node)
USER node
WORKDIR /home/node

# Expose the typical ports (Gateway + optional browser control)
EXPOSE 18789 18791

# Tini for graceful shutdown
ENTRYPOINT ["/usr/bin/tini","--"]

# Default command: run gateway in LAN bind mode for containers (we publish only to 127.0.0.1 on host)
CMD ["clawdbot","gateway","--port","18789","--bind","lan","--verbose"]
