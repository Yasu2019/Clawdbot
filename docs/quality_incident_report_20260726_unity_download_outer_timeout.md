# Unity installer chunk exceeded the outer timeout (2026-07-26)

## Impact and facts

The first F-drive resume command exceeded the shell's 50-second allowance and
returned after 54 seconds. The curl child continued transferring and stopped
naturally at 578,831,355 of 4,031,619,680 bytes (14.36%). The partial file is
valid for HTTP Range continuation. No unrelated process was changed.

## RCA

### 5 Whys

1. The shell command exceeded its allowance because curl was still active.
2. Curl was still active because `--max-time 35` applied per attempt.
3. A retry was enabled with `--retry 1`, allowing another attempt after timeout.
4. The combined worst case exceeded the 50-second outer allowance.
5. The command contract had not reserved time for retry and final status output.

FTA branches: insufficient disk space was ruled out (F: had about 1.63 TB free);
transfer stall was ruled out by growth from 430,643,904 to 578,831,355 bytes;
server failure was ruled out by successful Range continuation.

## FMEA

| Mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Inner retry exceeds outer timeout | 4 | 7 | 2 | 56 | Disable curl retry inside each chunk |
| Outer timeout leaves active child | 5 | 5 | 3 | 75 | Use 25 s inner / 40 s outer and verify PID |
| Partial file discarded | 6 | 2 | 2 | 24 | Preserve and use `--continue-at -` |

## Countermeasure plan

1. Keep the verified F-drive partial file.
2. Resume with `--retry 0 --max-time 25`.
3. Give the shell 40 seconds, leaving time to print and persist final size.
4. After each chunk, confirm byte growth; stop after three consecutive no-growth
   attempts.
5. At completion require exactly 4,031,619,680 bytes and a valid Unity
   Technologies Authenticode signature before installation.

Decision rule: IF an inner transfer can retry, THEN its worst-case duration must
remain below the outer harness timeout with status-write margin, BECAUSE an outer
timeout can orphan an otherwise healthy child.

## Verification, rollback, and scope

Pass for containment: curl PID exited naturally; file reached 14.36%; D-drive
partial remains preserved. Rollback is deletion of only the new F-drive partial,
but no deletion is currently authorized or needed.

Final verification completed at 2026-07-26T12:26:42+09:00:
4,031,619,680 bytes exactly, Authenticode status `Valid`, signer
`Unity Technologies SF`, and harness state `verified_complete`.

## Web knowledge decision and provenance

No additional web search was needed; the local process state and byte growth
proved the cause. Official download URL and expected size were already verified
from Unity's release infrastructure. Date: 2026-07-26 JST. Backup commit:
`e765bdedaf`.
