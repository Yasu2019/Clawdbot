# INC-167 Unity installer outer-timeout overrun

## QC / evidence

F: had about 1.63 TB free. The resumable Unity installer grew from 430,643,904
to 578,831,355 bytes (14.36%). Curl then exited naturally. Therefore this was a
harness-duration defect, not a disk-capacity, server, or no-progress failure.

## 5 Why / FTA / Fishbone

The outer timeout fired because curl remained active; curl remained active
because a 35-second per-attempt cap was combined with one retry; the aggregate
duration exceeded the 50-second harness allowance. Contributing method factor:
no explicit margin for result serialization. Machine, disk, and network remained
healthy because bytes continued to increase.

## FMEA

| Failure mode | S | O | D | RPN | Action |
|---|---:|---:|---:|---:|---|
| Retry exceeds harness | 4 | 7 | 2 | 56 | Retry 0 |
| Child outlives shell | 5 | 5 | 3 | 75 | 25 s inner / 40 s outer; PID check |
| Lost partial | 6 | 2 | 2 | 24 | Preserve and Range-resume |

## Countermeasure / gate

Resume only with 25-second, no-retry chunks. Persist size after every chunk and
stop after three consecutive no-growth attempts. Installation is forbidden until
size equals 4,031,619,680 bytes and the Unity Technologies Authenticode
signature is valid.

Rollback: remove only the F-drive partial if later authorized; the D-drive
partial remains. Scope: completion and signature are not yet proven. Source:
INC-167, backup commit `e765bdedaf`, 2026-07-26 JST.
