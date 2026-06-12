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
ALWAYS perform Visual QC (AI sight/image parsing) and mathematical coordinate checks (Stage layout) on the FIRST output frame of a 3D Base Render BEFORE passing it to AI Synthesis (ComfyUI/AnimateDiff) to prevent costly garbage generation. Reference `fmea_log.md` for 250 known failure modes.
ALWAYS perform Mecha/Robot Rigging Web Checks: Before starting modeling or rigging, thoroughly research the mechanics via web videos/documentation. List all movable ranges, pivot points (hinges), and specific armor attachments (e.g., knee pads on shins, multi-plate skirts) in a checklist to ensure strict structural compliance.
ALWAYS run `ue5_background_alignment_check.py` to mathematically verify that background actors (buildings, roads, lights) do not intersect with character actors and that lighting is dynamically aligned to prevent BG-001 clipping errors.
CRITICAL RULE (API QUOTA PROTECTION): AI Visual Confirmation (目視確認) MUST be strictly enforced at every stage (Modeling -> Pre-Render -> Video Synthesis). However, massive API consumption is strictly PROHIBITED. To satisfy both, the AI MUST use extreme sampling (e.g., checking only the 1st keyframe of a cut) or fallback to local lightweight Vision Models (e.g., LLaVA/Moondream on local nodes) before making any expensive paid API calls. Never send bulk video frames to cloud APIs.

------------------------------------------------
SYSTEM RESULT
------------------------------------------------

Codex + OpenClaw now operate with:

- persistent AI memory
- context retrieval
- reduced token usage
- faster reasoning

End Protocol
## Incident & Failure Management Rule (RCA Protocol)
If a past instruction is missed, a code failure occurs, or the user points out a quality incident, the AI MUST immediately:
1. Conduct a deep Root Cause Analysis (RCA) using frameworks such as:
   - 5 Whys (なぜなぜ分析)
   - Fishbone Diagram / Ishikawa (特性要因図)
   - Fault Tree Analysis (FTA)
   - Logical Tree (ロジカルツリー)
   - FMEA (Failure Mode and Effects Analysis)
2. Document the findings in a persistent .md artifact (e.g., quality_incident_report_XXX.md).
3. Explicitly define countermeasures and strict rules to prevent recurrence.
4. Record the rule in the relevant core files (like Beads, Byterover, or this MD file).
5. Always confirm the countermeasure implementation plan with the user before resuming execution.
