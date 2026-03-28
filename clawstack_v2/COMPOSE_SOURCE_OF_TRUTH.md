# Compose Source Of Truth

Updated: 2026-03-28

## Current rule

- `clawstack_v2/docker-compose.yml` is the active base compose for the current stack.
- Additive services should be layered with patch files instead of copying the full compose.
- Current example:
  - `clawstack_v2/docker-compose.learning_engine.patch.yml`

## Recommended commands

Base stack only:

```powershell
docker compose -f clawstack_v2/docker-compose.yml up -d
```

Base stack plus Learning Memory:

```powershell
docker compose -f clawstack_v2/docker-compose.yml -f clawstack_v2/docker-compose.learning_engine.patch.yml up -d
```

## Why this file exists

The top comments in `docker-compose.yml` became ambiguous over time while the live system continued using that file.
This note makes the intended operational rule explicit without forcing a risky large compose reorganization.

## Near-term guardrails

- Avoid duplicating the full compose into parallel variants.
- Prefer one base compose plus narrowly scoped patch files.
- Resolve host-port conflicts before enabling multiple optional tool profiles together.
