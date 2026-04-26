# HEARTBEAT.md

# Idle maintenance policy
# When the local LLM has no direct user work, it may do low-priority maintenance.
# Keep this bounded, quiet, and status-file based.

- Run `python3 /home/node/clawd/idle_ingest_maintenance.py` (or `/workspace/idle_ingest_maintenance.py` in n8n) when heartbeat arrives and it has been at least 30 minutes since the last heartbeat action.
- Do not spam outbound notifications just because heartbeat fired.
- Background maintenance is limited to:
  - email ingest freshness check and safe rerun only when stale
  - scheduled report DB sync when stale
  - cmux status refresh when stale
- Always write progress to `data/workspace/idle_ingest_maintenance_status.json`.
- If everything is fresh, reply `HEARTBEAT_OK`.
