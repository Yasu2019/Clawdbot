# Email Learning Memory Sync

This external harness syncs the existing `email_search.db` SQLite index into the new `learning_engine`.

## Script

- [`sync_email_learning_memory.py`](/D:/Clawdbot_Docker_20260125/data/workspace/sync_email_learning_memory.py)

## Input Sources

- `emails` table in `email_search.db`
- `tasks` table in `email_search.db`

## Output Targets

- `POST /ingest/email-message`
- `POST /ingest/email-thread`

## Runtime Files

- Status: [`email_learning_memory_sync_status.json`](/D:/Clawdbot_Docker_20260125/data/workspace/email_learning_memory_sync_status.json)
- State: [`email_learning_memory_sync_state.json`](/D:/Clawdbot_Docker_20260125/data/workspace/email_learning_memory_sync_state.json)

## Behavior

- Safe additive sync only
- If `learning_engine` is unavailable, the script records a skipped status and exits cleanly
- First run bootstraps recent data using `--bootstrap-days`
- Later runs use incremental sync based on `emails.indexed_at` and `tasks.updated_at`
- Message memories are written to `email_fact_memory`
- Thread rollups are written to `email_thread_memory`

## Example

```powershell
python data\workspace\sync_email_learning_memory.py --base-url http://localhost:8110 --source-org Mitsui --limit 50
```
