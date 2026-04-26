# Docker Add-ons Rollout

## Phase 1: Light
- `stirling_pdf`
- `actual_budget`
- `vikunja`
- `dashy`
- `ntfy`

## Phase 2: Medium
- `browserless`
- `changedetection`

## Phase 3: Heavy
- `immich_postgres`
- `immich_redis`
- `immich_machine_learning`
- `immich_server`

## Policy
- Install only one phase at a time.
- Verify `docker compose ps` after each phase.
- Verify HTTP response for each UI service before moving on.
- Do not start Phase 3 until disk and memory headroom are confirmed.
