---
tags: [gmail, oauth, concurrency, windows, incident]
incident: INC-148
trouble_id: T059
bd_key: Clawdbot_Docker_20260125-161t
updated: 2026-07-12
---

# Gmail concurrency and token race

## Summary

- NG: two independent backfills ran while the lock referenced a dead third PID.
- OK: native Windows liveness, owner-safe release, atomic JSON, and serialized refresh are implemented.
- Impact: intermittent 401 and connection failures; Gmail and DB data were preserved.

## QC工程表

| Control | Method | Acceptance | Result |
|---|---|---|---|
| Live PID | mocked Windows live owner | contender cannot acquire | PASS |
| Dead PID | mocked dead owner | stale lock replaced | PASS |
| Ownership | replace payload before release | old owner cannot unlink | PASS |
| Token file | atomic save test | valid JSON and no temp residue | PASS |
| Gmail health | profile GET | read-only success | PASS |

## FMEA

| Failure mode | Effect | Cause | Countermeasure |
|---|---|---|---|
| Live lock removed | duplicate backfill | non-portable PID probe | Windows OpenProcess |
| New owner lock deleted | concurrency reappears | unconditional release | exact payload check |
| Partial token JSON | authentication outage | direct file write | temp plus os.replace |
| Refresh storm | 401/429 amplification | concurrent refresh | dedicated refresh lock |

## 5 Why / FTA

Gmail failed intermittently because clients ran concurrently; concurrency occurred because a live lock was cleared; it was cleared because `os.kill(pid, 0)` was assumed portable; Windows semantics were not tested; the lock was treated as utility code rather than a safety gate.

FTA: intermittent access = authentication race OR concurrent quota pressure OR network failure. Separate bounded gates now cover all three branches.

## Fishbone

- Method: multiple independent launch paths.
- Machine: Windows PID semantics.
- Software: unconditional lock release and direct JSON writes.
- Measurement: process presence was inferred incorrectly.
- Environment: remote disconnects and Gmail quota limits.

## Countermeasures and forbidden patterns

- Keep one independent full-backfill root.
- Do not use `os.kill(pid, 0)` as the Windows process gate.
- Do not unlink a lock without matching ownership.
- Do not write shared token JSON directly.
- Do not add unlimited API retries.

## Links

- `data/workspace/email_db_lock.py`
- `data/workspace/email_search_index.py`
- `quality_incident_report_20260712_gmail_concurrency.md`
- `docs/INCIDENT_LOG.md` INC-148
- `data/workspace/memory/trouble_history.md` T059
