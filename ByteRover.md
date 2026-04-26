# PROTOCOL: Install ByteRover Long-Term Memory for Codex + OpenClaw

Goal:
Enable persistent long-term memory for Codex, OpenClaw and Antigravity agents
using ByteRover memory layer.

Environment:
- Windows 11 MiniPC
- Docker installed
- OpenClaw running in Docker
- Antigravity running outside Docker
- Codex CLI used in VS Code

Expected Result:
- AI agents automatically store knowledge
- Context retrieved automatically
- MEMORY.md no longer grows infinitely
- token usage optimized


------------------------------------------------
STEP 1 — Install ByteRover CLI
------------------------------------------------

Install Node dependency globally.

Run:

npm install -g byterover-cli

Verify install:

brv --version


------------------------------------------------
STEP 2 — Initialize ByteRover Workspace
------------------------------------------------

Inside your main AI workspace folder run:

brv init

This creates:

.brv/
.brv/context-tree/


------------------------------------------------
STEP 3 — Install connectors for agents
------------------------------------------------

Install connector for Codex CLI:

brv connectors install "Codex"

Install connector for OpenClaw:

brv connectors install "OpenClaw"

Install connector for Antigravity:

brv connectors install "Antigravity"

Verify:

brv connectors list


------------------------------------------------
STEP 4 — Enable automatic memory storage
------------------------------------------------

Create file:

AI_MEMORY_POLICY.md

Content:

# ByteRover Memory Rules

Before executing any complex task:
1. Query ByteRover memory

Use command:

brv query "<topic>"

After completing important tasks:
2. Store key knowledge

Use command:

brv curate "<knowledge summary>"


------------------------------------------------
STEP 5 — Create automatic memory cron
------------------------------------------------

Create script:

scripts/memory_mining.sh

Content:

brv curate "summarize important development decisions from today's sessions"


Schedule daily job.

Linux / WSL example:

crontab -e

Add:

0 3 * * * bash ~/scripts/memory_mining.sh


------------------------------------------------
STEP 6 — Connect Docker OpenClaw memory hook
------------------------------------------------

Edit docker-compose.yml

Add environment variable:

environment:
  - BYTE_ROVER_ENABLED=true
  - BYTE_ROVER_PATH=/workspace/.brv

Restart containers:

docker compose down
docker compose up -d


------------------------------------------------
STEP 7 — Test memory system
------------------------------------------------

Store memory:

brv curate "OpenClaw docker environment installed on MiniPC"

Query memory:

brv query "OpenClaw docker environment"


Expected result:
ByteRover returns stored knowledge.


------------------------------------------------
STEP 8 — AI instruction rule
------------------------------------------------

Add to Codex system prompt:

ALWAYS query ByteRover memory before complex tasks.
ALWAYS store important solutions into ByteRover memory.


------------------------------------------------
SYSTEM RESULT
------------------------------------------------

Codex + OpenClaw now operate with:

- persistent AI memory
- context retrieval
- reduced token usage
- faster reasoning

End Protocol