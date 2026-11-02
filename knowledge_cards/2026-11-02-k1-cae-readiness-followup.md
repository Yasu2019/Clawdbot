# Sanitized compute readiness follow-up — 2026-11-02 JST

An authenticated read-only check of a Windows/WSL compute node found an existing non-solver worker still running and its progress log advancing. A bounded output inventory and fixed source scan did not verify a native checkpoint; this does not rule out an external recovery mechanism and does not prove the worker is stalled. Preserve existing work until ownership and recovery are confirmed.

The node reports 16 GiB installed RAM and about 15.42 GiB OS-visible. A health snapshot showed about 1.26 GiB available, while a direct Windows sample taken later showed about 4.32–4.34 GiB. These were not simultaneous; do not combine them or treat either as a stable budget. Private Bytes were about 24.36 GB while working set was about 7.55 GB; commit and resident memory are different measures.

CPU was 11.45% over about 2 seconds across 12 logical processors. The thermal gate used the sensor label Core (Tctl/Tdie): its trailing five-minute time-weighted mean was 89.29 C, with a 95 C gate. Core Average and fan values were unavailable, so this is not evidence of fan speed or Core Average. No WSL solver process was observed and dispatch remained disabled.

Decision: preserve the running work and hold new FEM dispatch pending authorization, case-specific resource budgeting, and verified solver-native checkpoint/restart evidence. Root cause for historical memory variation remains UNKNOWN. This sanitized note omits host identity, addresses, accounts, process IDs, internal paths, raw logs and credentials. Source: reviewed live follow-up note INC-K1MMENT-K1-CAE-READINESS-FOLLOWUP-20261102T1048JST.md.
