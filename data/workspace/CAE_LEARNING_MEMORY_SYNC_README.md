# CAE Learning Memory Sync

This external harness syncs CAE solver logs into the `learning_engine`.

## Script

- [`sync_cae_learning_memory.py`](/D:/Clawdbot_Docker_20260125/data/workspace/sync_cae_learning_memory.py)

## Current Input

- [`openradioss_run.log`](/D:/Clawdbot_Docker_20260125/data/workspace/openradioss_run.log)
- [`apps/molding_hub/test_sim/CFD_MeltFront/case.foam`](/D:/Clawdbot_Docker_20260125/data/workspace/apps/molding_hub/test_sim/CFD_MeltFront/case.foam)

## Output Target

- `POST /ingest/cae-run`

## Runtime Files

- Status: [`cae_learning_memory_sync_status.json`](/D:/Clawdbot_Docker_20260125/data/workspace/cae_learning_memory_sync_status.json)
- State: [`cae_learning_memory_sync_state.json`](/D:/Clawdbot_Docker_20260125/data/workspace/cae_learning_memory_sync_state.json)

## Behavior

- Safe additive sync only
- If `learning_engine` is unavailable, the script records a skipped status and exits cleanly
- Parses OpenRadioss engine logs into a normalized CAE run payload
- Parses OpenFOAM case directories into a normalized CAE run payload
- Writes to `cae_run_memory`
- Keeps the implementation outside core Docker compose
- `idle_ingest_maintenance.py` can invoke the sync when CAE learning memory is stale

## Example

```powershell
python data\workspace\sync_cae_learning_memory.py --base-url http://localhost:8110 --source-org Mitsui
```
