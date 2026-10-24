# Incident orca-local-1w8: ByteRover curate false-success status

- Observed: 2026-10-24 14:32:49 +0900 (Asia/Tokyo)
- Source: K10; `D:/Clawdbot_Docker_20260125/data/workspace/safe_brv_curate.py`, ByteRover CLI `brv status` / `brv curate`, and direct wrapper output.
- Symptoms: `brv status` reported `Account: Session expired` and `Space: Not connected`. The safe wrapper treated that status as logged in, then attempted a bounded curate. The CLI returned exit code 0 but stdout explicitly reported `All 4 retry attempts exhausted: Cannot connect to API: connect ECONNREFUSED 127.0.0.1:11434`. The wrapper incorrectly labelled the operation `curated`.
- Impact: no evidence that content reached ByteRover; do not treat the result as synchronized. The local Markdown and curated read-only MCP export are preserved. A local retry-queue record is being added; remote status remains pending.
- Root cause: confirmed wrapper logic recognized only nonzero exit codes and a narrow set of text markers; it did not treat expired sessions or retry-exhaustion/connection-refusal text as failure.
- Prior state: incident card `INC-PP-SHORTSHOT-DATA-20261024-01.md` was being synced. No unrelated process, scheduled job, calculation, or user file was stopped or overwritten.

## Correction and verification

- `is_logged_in()` now requires an account line and rejects `Session expired`, `Not connected`, and `Not authenticated` states.
- Added `curate_failed()` to recognize timeouts, nonzero exits, retry exhaustion, `Cannot connect to API`, `ECONNREFUSED`, authentication failure, HTTP failure, and provider unavailable output even if the CLI exits zero.
- Wrapper now records `queued_after_failure` instead of claiming success for detected failure text.
- Six focused unit tests pass, covering expired, missing and connected account states; zero-exit retry-exhaustion failure; normal success; and timeout.
- The earlier direct provider attempt is not retried. The next call to the patched safe wrapper observes the expired session and queues locally without calling curate.

## FMEA draft (S/O/D and RPN unassessed)

- Failure mode: sync provider fails while wrapper reports success.
- Effect: user believes operational knowledge reached remote memory when only local notes exist.
- Cause: incomplete session-state and response-text classification (confirmed).
- Prevention/detection: fail closed for expired account state; detect provider error text independently of exit code; durable local queue; regression tests.
- Owner: unassigned. Validation: six local unit tests pass.
- Residual risk: unknown future provider error wording may escape text markers; external sync must still be verified by remote read-back.

## FTA draft

Top event: knowledge synchronization is falsely reported as complete.

- A: session expired is accepted as authenticated ? confirmed, corrected/tested.
- B: CLI exits zero despite provider failure text ? confirmed, corrected/tested.
- C: provider emits a new unrecognized failure message ? open.
- D: successful local CLI response is not remotely persisted ? open until provider-side read-back.

## QC process chart draft

- Step: submit sanitized reviewed knowledge card through safe ByteRover wrapper.
- Gate: inspect account state, process result and provider response text; distinguish local queue from remote success.
- Method: `safe_brv_curate.py`, regression tests and post-success remote read-back.
- Criteria: expired/not-connected account or any detected provider failure must result in local pending queue; only a confirmed success/read-back may be marked synchronized.
- Record: status JSON, local queue item, incident note, test report.
- Escalation: if classification is uncertain, preserve pending status and do not claim remote completion.

## Control Plan draft

- Characteristic: sync outcome state.
- Method/frequency: check every curation invocation.
- Acceptance: authenticated status; no timeout/error marker; provider evidence or read-back for remote-complete claim.
- Reaction: append one deduplicated pending local queue item; defer cloud retry until authorized session/provider is available.
- Owner: unassigned. Effectiveness: classification tests pass; end-to-end remote write/read-back remains unverified.

## GitHub publication verification (2026-10-24 14:42 JST)

The sanitized card was published together with the related PP data incident on `https://github.com/Yasu2019/Clawdbot/tree/knowledge/pp-shortshot-data-quality-20261024`. Fetched remote head matches commit `61dfe14d9b202c8b57776d80202e6adb6bf757b7`; read-back SHA-256 for this card is `4b83a72f70320b8071b810b5d26be8bf45e0c4b6f502326db6af9ee9855e5123`, equal to local source bytes. ByteRover remote remains pending; local queue is verified.
