# Adoption Decision Protocol

## Objective
This protocol tells a coding agent (Claude Code, Codex CLI, Antigravity, etc.) how to decide whether Kimi K2.6 should be:
- fully adopted
- partially integrated
- held for later

The agent must NOT blindly install. It must inspect conflicts first.

## Mandatory decision criteria
The receiving agent must check all of the following:

### A. Existing architecture conflicts
Check for collisions with:
- current docker-compose files
- current LiteLLM routing
- current Portal cards/apps
- current environment variable names
- current auth flow / bearer token logic
- current tracing callbacks to Langfuse
- current n8n workflows
- current Ollama/OpenAI-compatible endpoints

### B. Resource feasibility
Estimate:
- VRAM/RAM needs for intended Kimi deployment mode
- expected concurrent job count
- CPU/RAM pressure on existing services
- disk footprint for model weights/logs/cache
- whether current machine can host the selected mode without destabilizing the stack

### C. Security fit
Classify data classes:
- public
- internal low-risk
- confidential business
- customer confidential
- regulated/sensitive

Kimi remote API must be blocked for confidential and above.

### D. Operational value
Kimi should only be adopted when it offers at least one of the following improvements:
- much lower cost for batch tasks
- materially higher throughput on multi-file tasks
- better long-context handling
- better autonomous decomposition
- lower latency under the user's workflow style

## Required output from the receiving agent
The receiving agent must produce a short decision report with:
- ADOPT / PARTIAL / HOLD
- reasons
- blocked items
- next implementation scope
- rollback path

## Decision rules
### Choose ADOPT when:
- no major port/conf file collisions
- deployment path is practical
- security boundaries can be enforced
- Kimi adds clear throughput or cost advantage

### Choose PARTIAL when:
- Kimi is useful, but only for a subset of workloads
- local hosting is not yet practical
- remote API is allowed only for non-sensitive tasks
- orchestration needs phased rollout

### Choose HOLD when:
- hardware is inadequate for intended mode
- security policy cannot be enforced
- it duplicates existing capability with little gain
- operational complexity outweighs benefit

## Preferred recommendation for this environment
Likely answer: PARTIAL to ADOPT in phased form

Phase target:
- Phase 1: batch worker only
- Phase 2: n8n autonomous jobs
- Phase 3: optional swarm orchestration
- Phase 4: portalized QA automation
