# Mini PC Mode

Updated: 2026-03-28

## Goal

Keep the core Clawstack workflows responsive on a Mini PC by stopping optional heavyweight services when they are not actively needed.

## What is considered core

- `clawdbot-gateway`
- `quality_dashboard`
- `learning_engine`
- `postgres`
- `redis`
- `qdrant`
- `n8n`
- `portal_server`
- task-specific apps that you are actively using

## What is treated as optional/heavy

The optimizer script targets large or overlapping services such as:

- `infinity`
- `docling`
- `clickhouse`
- `langfuse*`
- `dify*`
- `open_notebook*`
- `paperless`
- `crawl4ai`
- `metabase`
- `immich*`
- `redis-stack`
- `nodered`
- `portainer`
- `dozzle`
- `uptime-kuma`

## Commands

Capture current heavy-service status:

```powershell
python data/workspace/minipc_optimizer.py status
```

Apply conservative Mini PC mode:

```powershell
python data/workspace/minipc_optimizer.py apply-lite
```

## Output

The script writes:

- `data/workspace/minipc_optimizer_status.json`

That file can be checked later to see which services were considered heavy and which ones were stopped.

## Notes

- This harness is intentionally external and reversible.
- It does not rewrite the core compose.
- It is designed to reduce idle RAM/CPU pressure without touching the main project logic.
