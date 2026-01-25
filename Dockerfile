FROM node:22-bookworm-slim

# Minimal OS deps (curl for health checks / debugging, tini for clean PID1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tini git \
  && rm -rf /var/lib/apt/lists/*

# Install Clawdbot CLI (pin if you want: npm install -g clawdbot@2026.1.22)
RUN npm install -g clawdbot

# Run as non-root user (node)
USER node
WORKDIR /home/node

# Expose the typical ports (Gateway + optional browser control)
EXPOSE 18789 18791

# Tini for graceful shutdown
ENTRYPOINT ["/usr/bin/tini","--"]

# Default command: run gateway in LAN bind mode for containers (we publish only to 127.0.0.1 on host)
CMD ["clawdbot","gateway","--port","18789","--bind","lan","--verbose"]
