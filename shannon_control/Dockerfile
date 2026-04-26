FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI (Shannon needs it to spawn worker containers)
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz \
    | tar -xz --strip-components=1 -C /usr/local/bin docker/docker

WORKDIR /app

COPY package.json .
RUN npm install --production

# Pre-install Shannon CLI to avoid cold-start delay
RUN npx --yes @keygraph/shannon --version 2>/dev/null || true

COPY server.js .
COPY public/ public/

EXPOSE 5002
CMD ["node", "server.js"]
