# Implementation Steps

## Phase 0 - Snapshot and backup
Before any change:
1. export current docker compose files
2. back up .env files
3. export current n8n workflows if modified in production
4. record running containers and ports
5. record current LiteLLM model config
6. record current Portal cards/apps list

Suggested commands:
```bash
docker compose ps
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
docker compose config > compose.snapshot.yaml
```

## Phase 1 - Add Kimi as non-default worker model
Goal:
- Add Kimi endpoint without changing current default model behavior

Tasks:
1. add KIMI_API_BASE and KIMI_API_KEY to env
2. add a named worker model in LiteLLM config
3. do not route default traffic to it yet
4. add health-check/test prompt route
5. log results to Langfuse if already enabled

## Phase 2 - Add controlled routing
Goal:
- Route only selected workloads to Kimi

Suggested initial workloads:
- batch summarization
- multi-file code explanation
- PDF collection review
- first-pass issue clustering

Rules:
- non-sensitive only
- max token and timeout guardrails enabled
- workflow kill switch enabled

## Phase 3 - Add autonomous n8n flows
Create workflows for:
- nightly document digest
- incoming PDF triage
- defect trend analyzer
- audit evidence extractor

Each workflow must include:
- input classifier
- privacy classifier
- Kimi route eligibility check
- output reviewer step
- logging step
- alert step on failure

## Phase 4 - Add portal entry points
Add a Portal card such as:
- Kimi Worker Hub
- QA Batch Review Hub
- Autonomous Audit Assistant

Each card should show:
- queue status
- last run
- success/failure
- model used
- escalation state

## Phase 5 - Swarm mode (optional)
Only after stability:
- split one big task into many subtasks
- run parallel workers with capped concurrency
- gather all outputs into one reviewer step
- deduplicate overlapping answers

Cap concurrency conservatively at first.
Recommended initial cap:
- 3 to 5 workers
Not 300.

## Phase 6 - Harden and document
Finalize:
- SOP
- rollback guide
- operator checklist
- data classification note
- prompt inventory
