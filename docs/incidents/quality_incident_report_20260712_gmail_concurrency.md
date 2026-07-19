# Gmail concurrency and token race RCA - INC-148

Date: 2026-07-12 JST

## Confirmed facts

- Two independent priority-backfill roots were observed.
- The operation lock named a third, dead PID while an old backfill remained active.
- Windows process existence used `os.kill(pid, 0)`.
- All Gmail paths shared `data/workspace/token.json`.
- Google documents 401 for invalid credentials and concurrent-client/rate-limit failures for excessive simultaneous mailbox access.

## Root cause

The Windows PID probe falsely classified a live lock owner as dead. A later worker removed the live lock and started concurrently. Shared access-token state could then diverge between process memory and disk, while concurrent Gmail traffic increased transient failure probability.

## Countermeasures

- Native Windows liveness check using `OpenProcess`.
- Exact owner-payload check before lock deletion.
- Dedicated token-refresh lock and disk-token reload.
- Atomic JSON replacement.
- One refresh replay for 401 and bounded idempotent transient retry.
- Single logical priority-backfill root.

## Verification

- Focused tests: 10/10 PASS.
- Orphan PID 6048 stopped.
- Replacement logical worker active with lock owner PID 35796.
- Gmail read-only profile request: PASS.
