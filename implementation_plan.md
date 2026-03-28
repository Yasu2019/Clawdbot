# Nested Learning Implementation Plan

Date: 2026-03-26
Scope: `OpenClaw_Learning_Protocol_Pack.zip` Phase 1 bootstrap

## Goal

Add a safe first version of a `learning_engine` that can:

- ingest structured case memory
- compare a new case against past similar cases
- capture judgement feedback
- search stored memories

without directly modifying the core `docker-compose.yml` yet.

## Constraints

- Respect `AGENTS.md`: avoid editing core compose until the implementation plan exists.
- Keep current services stable.
- Reuse the existing stack where possible:
  - `qdrant`
  - `litellm`
  - `langfuse`
  - `n8n`
  - `paperless`
  - `docling`
  - `ollama`

## Phase 1 Deliverables

1. New service scaffold at `clawstack_v2/docker/learning_engine`
2. FastAPI endpoints:
   - `GET /health`
   - `POST /ingest/case`
   - `POST /compare/case`
   - `POST /feedback/judgement`
   - `POST /search/memory`
3. Qdrant-backed storage with auto-create collections
4. Deterministic fallback embedding path so the service can run even before model wiring is finished
5. Portal app scaffold at `data/workspace/apps/learning_memory/index.html`
6. Separate compose patch file for later activation

## Out of Scope For This Pass

- Direct edits to the core `clawstack_v2/docker-compose.yml`
- Full Email ingest workflow
- Full CAE/FEM ingest workflow
- Production-grade access control and review workflow
- Cross-org lesson generalization automation

## Success Criteria

- The learning engine code is runnable and syntax-valid
- Core endpoints behave consistently with the protocol pack
- The implementation is additive and reversible
- The repo is ready for a later compose activation step

## Phase 2 Extension Notes

- Add `POST /ingest/quality-issue`
- Add `POST /ingest/improvement-activity`
- Create Qdrant collections for `quality_issue_memory` and `improvement_activity_memory`
- Keep the activation path additive through `clawstack_v2/docker-compose.learning_engine.patch.yml`

## Phase 3 Extension Notes

- Add `POST /ingest/email-message`
- Add `POST /ingest/email-thread`
- Add `POST /compare/email-thread`
- Create Qdrant collections for `email_fact_memory` and `email_thread_memory`
- Keep email ingest compatible with the existing external-harness and n8n patterns

## Phase 4 Extension Notes

- Add `POST /ingest/cae-run`
- Add `POST /compare/cae-run`
- Create Qdrant collection for `cae_run_memory`
- Add an external CAE sync harness so existing solver logs can be summarized without changing core compose
- Extend the CAE sync harness to normalize OpenRadioss logs and OpenFOAM case directories
- Let `idle_ingest_maintenance.py` trigger CAE learning sync when the status file is stale

## 2026-03-28 Operational Hardening Notes

- Clarify that `clawstack_v2/docker-compose.yml` remains the active base compose for the current stack, with additive patch files layered on top.
- Fix maintenance reliability before adding more automation:
  - make `scheduled_report_search.py` tolerant to host/container n8n API base differences
  - make SQLite initialization fall back when WAL is unsupported on mounted storage
  - make `update_cmux_status.py` resolve the repository root robustly from both host and `/workspace` paths
  - make nightly email ingest notifications surface timeout/degraded states instead of always sounding successful
- Resolve latent host port conflicts inside the `tools` profile so the stack is predictable when optional tools are enabled together.
- Add an external Mini PC optimization harness and runbook rather than baking aggressive stop/start behavior into core compose.
