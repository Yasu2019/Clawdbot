# Managed FEM host repeat-counter and worker follow-up ? 2026-11-02 11:18?11:19 JST

Linked incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01`.

- Three consecutive host samples showed PerfOS/PSAPI commit counters aligned near31.20/36.115GB. A later sample aligned near31.20/35.242GB. Available RAM moved from ~2.4GB to ~1.1GiB; current host capacity remains low. Cause of the change is UNKNOWN.
- One worker private-bytes observation at11:18:51 read12.89GiB, but two same-PID follow-ups agreed at22.693GiB from both WMI and GetProcess. Treat the isolated low value as an unreproduced outlier; do not infer a real release or growth.
- The existing worker remained CPU-active while its progress log stayed at step640, last written11:10:32. Quiet logging does not prove a hang. No in-case checkpoint/restart path has been verified; preserve the job and do not claim it is resumable.
- Health at11:18:20: CPU18.02% over2.016s/12 logical processors; available RAM1.58GiB; Tctl/Tdie88.25C. At11:19 the five-minute mean was89.816C/95 and accepted. Core Average and fan values remain unavailable; this does not verify maximum cooling.
- A prior isolated ~3.39GB commit-counter mismatch did not reproduce in repeated samples. The cause remains UNKNOWN and is not considered fixed. New FEM dispatch remains disabled.

Durable local evidence keeps exact task/process identity and raw observations. This shared card is sanitized and omits those identifiers. No work was stopped or restarted and no setting changed.
