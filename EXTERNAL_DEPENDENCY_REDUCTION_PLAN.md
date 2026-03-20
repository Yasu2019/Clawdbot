# External Dependency Reduction Plan

## Goal
Reduce external API usage and increase agent autonomy in this workspace.

This document only targets:
- API cost reduction
- fewer approval / intervention points
- more stable local-first execution

It does not target:
- UI polish
- feature expansion
- documentation cleanup unless it affects runtime decisions

## Current Assessment

The environment is already partly local-first:
- `Codex` is configured with `approval_policy = "never"` in `C:\Users\yasu\.codex\config.toml`
- `OpenClaw` defaults to local Ollama models in `data/state/openclaw.json`
- the monitoring chain is local: `Changedetection -> ntfy -> Vikunja -> n8n`

However, external dependencies still remain in three forms:
- active runtime configuration that still exposes external model providers
- automation files and workflow generators that still contain direct external API calls
- legacy workflow exports / docs that can mislead future regeneration or maintenance

## Priority Order

### P0: Active runtime dependencies to isolate first

1. `data/state/litellm_config.yaml`
   - Current issue:
     - still exposes `gemini`, `groq`, and `cerebras`
   - Why it matters:
     - these models remain callable through LiteLLM even if OpenClaw defaults to local
     - future workflows or scripts can silently route to paid APIs
   - Action:
     - move external providers into a separate `litellm_config.external.yaml`
     - keep default runtime config local-only
   - Target state:
     - default loaded config contains only Ollama and local embedding routes

2. `docker-compose.yml`
   - Current issue:
     - still injects `GEMINI_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`
   - Why it matters:
     - external providers remain armed by environment
   - Action:
     - stop passing external API keys to default services unless explicitly needed
     - reserve them for an opt-in profile or override file
   - Target state:
     - normal startup does not include paid model keys

### P1: Active automation paths to convert next

3. `data/workspace/workflow_healer.py`
   - Current issue:
     - direct Telegram Bot API call
   - Why it matters:
     - external dependency for routine healing notifications
   - Action:
     - route notifications through local `ntfy` first
     - keep Telegram only as optional downstream alert

4. `data/workspace/create_healer_workflow.py`
   - Current issue:
     - embeds direct Telegram Bot API URL
   - Why it matters:
     - regenerated workflows will keep external notification hardwired
   - Action:
     - generate `ntfy` or local webhook based notifications by default

5. `data/workspace/create_ai_scout_workflow.py`
   - Current issue:
     - template still contains `google/gemini-2.5-flash`
     - template also contains Telegram API send step
   - Why it matters:
     - even if later replaced programmatically, the source template is still externally biased
   - Action:
     - rewrite template source to be local-first at definition time
     - use Ollama model names directly in generated body
     - use `ntfy -> n8n -> Telegram` only if Telegram delivery is explicitly required

6. `scripts/telegram_fast_bridge.ps1`
7. `scripts/telegram_fast_bridge_v2.ps1`
8. `scripts/telegram_fast_bridge_v3.ps1`
   - Current issue:
     - direct Telegram polling and send calls
   - Why it matters:
     - necessary if Telegram is a required channel, but still an external dependency
   - Action:
     - keep only one active bridge version
     - archive or disable old bridge variants
     - make all nonessential notifications local-first through `ntfy`
   - Target state:
     - Telegram remains an intentional edge channel, not the default notification bus

### P2: Workflow exports and dormant-but-dangerous assets

9. `data/workspace/p016.json`
10. `data/workspace/p016_fixed.json`
11. `data/workspace/tmp/p016.json`
   - Current issue:
     - active workflow exports contain direct Telegram API calls
     - Gmail ingestion remains external by nature
   - Why it matters:
     - re-import or copy-paste can reintroduce external routing
   - Action:
     - mark as legacy
     - create local-first successor flow definition
     - send reports to local storage / ntfy / Vikunja first

12. `data/workspace/scripts/scheduled_notify.py`
   - Current issue:
     - direct Telegram API send
   - Why it matters:
     - routine notifications leak into an external channel by default
   - Action:
     - switch to local notification fan-out

### P3: Documentation that can bias future changes

13. `data/workspace/PORTAL_APPS.md`
14. `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v1.md`
15. `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v2.md`
16. `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v2.1.md`
17. `data/workspace/docs/observability_plan_v1.md`
18. `data/workspace/DUAL_AGENT_PROTOCOL.md`
19. `data/workspace/Nightly_Report.md`
20. `README.md`
   - Current issue:
     - still describe Gemini / Groq as normal-path models
   - Why it matters:
     - future maintenance can drift back to paid APIs
   - Action:
     - rewrite operational docs so local Ollama is the standard path
     - move paid APIs into a clearly labeled emergency / optional section

## Autonomy Assessment by Agent

### Codex
- Status: mostly autonomous
- Evidence:
  - `C:\Users\yasu\.codex\config.toml` uses `approval_policy = "never"`
- Remaining limiter:
  - external services and scripts can still introduce runtime dependence outside Codex itself

### OpenClaw
- Status: partially autonomous
- Evidence:
  - `data/state/openclaw.json` defaults to local Ollama
- Remaining limiter:
  - LiteLLM still exposes external models
  - old workflow templates can regenerate external calls

### Claude Code
- Status: partially autonomous
- Evidence:
  - `C:\Users\yasu\.claude\settings.json` uses `permissions.defaultMode = "acceptEdits"`
  - only a limited allowlist is configured
- Remaining limiter:
  - broader commands still need approval unless explicitly allowlisted
  - this is not equivalent to Codex `never`

## Recommended Target State

### Local-first runtime
- default LLM path:
  - Ollama only
- default notifications:
  - `ntfy`
- default automation:
  - local `n8n`, `Vikunja`, `Dashy`, `Paperless`
- optional edge channels:
  - Telegram
- optional paid models:
  - isolated in separate config file and not loaded by default

### Approval-minimized operation
- Codex:
  - already close to target
- OpenClaw:
  - remove external model exposure from default runtime
- Claude Code:
  - expand safe local allowlist only for repeatable commands actually used in this repo
  - do not broadly bypass all permissions

## Concrete File-Level Actions

### High impact, low risk
- `data/state/litellm_config.yaml`
  - remove external providers from default config
- `data/workspace/create_ai_scout_workflow.py`
  - replace external-first template definitions with local-first definitions
- `data/workspace/workflow_healer.py`
  - replace default Telegram send with `ntfy`
- `data/workspace/create_healer_workflow.py`
  - generate local-first alerts
- `scripts/telegram_fast_bridge_v2.ps1`
  - retire
- `scripts/telegram_fast_bridge.ps1`
  - retire if `v3` is the only maintained path

### Medium impact
- `docker-compose.yml`
  - stop injecting paid API keys into default services
- `data/workspace/scripts/scheduled_notify.py`
  - convert to local bus
- `data/workspace/p016.json`
  - mark legacy / replace
- `data/workspace/p016_fixed.json`
  - mark legacy / replace

### Low runtime impact but important for drift prevention
- `README.md`
- `data/workspace/PORTAL_APPS.md`
- `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v1.md`
- `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v2.md`
- `data/workspace/CLAWSTACK_SYSTEM_PROTOCOL_v2.1.md`
- `data/workspace/docs/observability_plan_v1.md`
- `data/workspace/DUAL_AGENT_PROTOCOL.md`

## Not a Reduction Target

These are external by nature and should be treated as intentional edge dependencies, not mistakes:
- Telegram transport itself, if user-facing Telegram delivery is required
- Gmail nodes, if mailbox sync is required
- external websites monitored by `Changedetection`

The goal is not zero external traffic.
The goal is to avoid paying for inference or relying on external APIs for normal internal orchestration.

## Suggested Next Execution Batch

Batch 1:
- `data/state/litellm_config.yaml`
- `data/workspace/create_ai_scout_workflow.py`
- `data/workspace/workflow_healer.py`
- `data/workspace/create_healer_workflow.py`

Batch 2:
- `docker-compose.yml`
- `data/workspace/scripts/scheduled_notify.py`
- retire old Telegram bridge variants

Batch 3:
- workflow export cleanup
- documentation realignment

## Memory Policy Note

This plan is durable operational knowledge and is safe to summarize into ByteRover.
Do not store raw API keys, tokens, or personal message contents.
