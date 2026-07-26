# INC-168 Unity download observer defects

## QC facts and RCA

The transfer harness remained healthy. Only observer commands failed: `-match`
parsed the literal Windows path and rejected `\C`; a later `Get-Content` collided
with a short `Set-Content` lock. File growth continued through both events.

The observer failed because a filesystem path was treated as regex. The JSON
read failed because the status writer was non-atomic and the observer had no
retry. Neither failure propagated to the background harness.

## FMEA and countermeasures

| Mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Invalid path regex | 2 | 5 | 1 | 10 | Use fixed PID or literal comparison |
| Status read lock | 2 | 5 | 1 | 10 | Retry five times at 300 ms |
| Observer stops worker | 8 | 2 | 2 | 32 | Keep observer read-only and separate |

Decision rule: IF monitoring a known background process, THEN use its fixed PID
and make status reads lock-tolerant, BECAUSE observer failures must never alter
the worker.

## Verification / rollback / scope

Progress was subsequently observed from 26.33% through 100%. Final file size was
4,031,619,680 bytes and Authenticode was valid for Unity Technologies SF.
No rollback was needed. This record covers observer behavior only.
