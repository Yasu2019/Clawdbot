# Learning Engine

Phase 1 scaffold for Nested Learning.

## Included now

- FastAPI service
- Qdrant-backed memory storage
- Deterministic fallback embedding
- Endpoints:
  - `GET /health`
  - `POST /ingest/case`
  - `POST /ingest/quality-issue`
  - `POST /ingest/improvement-activity`
  - `POST /ingest/email-message`
  - `POST /ingest/email-thread`
  - `POST /ingest/cae-run`
  - `POST /compare/case`
  - `POST /compare/email-thread`
  - `POST /compare/cae-run`
  - `POST /feedback/judgement`
  - `POST /search/memory`

## Next wiring targets

- core compose activation
- OpenFOAM/OpenRadioss CAE ingest refinement
- review queue
- Langfuse tracing hooks
- LiteLLM generation hooks

## Suggested activation

Use the separate patch file:

- [`clawstack_v2/docker-compose.learning_engine.patch.yml`](/D:/Clawdbot_Docker_20260125/clawstack_v2/docker-compose.learning_engine.patch.yml)

Example:

```powershell
docker compose -f clawstack_v2/docker-compose.yml -f clawstack_v2/docker-compose.learning_engine.patch.yml up -d learning_engine
```
