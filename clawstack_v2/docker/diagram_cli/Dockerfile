FROM node:20-slim
RUN apt-get update && apt-get install -y --no-install-recommends graphviz ca-certificates fonts-dejavu && rm -rf /var/lib/apt/lists/*
RUN npm i -g @mermaid-js/mermaid-cli markmap-cli
WORKDIR /work
