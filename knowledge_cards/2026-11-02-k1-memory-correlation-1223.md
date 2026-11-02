# K1 direct RAM and exact worker correlation — 2026-11-02 12:23 JST

Incident linkage: INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01; preserved legacy task OF76_f3A.

The WMI-free MemoryCapacityNativeLite probe now samples kernel32 GlobalMemoryStatusEx and the exact process PID2196 in one remote read. Process identity is guarded by PID, name python, and recorded start time (2026-11-02T02:00:12.1863044+09:00); no WMI, owner, parent, or command line. This is a read-only probe change, validated on K1. It records no raw task/source code.

| K10-observed time (JST) | Windows available physical bytes | PID2196 Private Bytes | PID2196 working set | PID CPU seconds |
|---|---:|---:|---:|---:|
| 12:21:48.065 | 967,155,712 | 24,369,127,424 | 8,529,932,288 | 35,874.5 |
| 12:22:14.740 | 2,574,147,584 | 24,369,127,424 | 7,646,613,504 | 35,900.5 |
| 12:23:00.152 | 1,122,152,448 | 24,369,168,384 | 10,246,897,664 | 35,944.4 |

Across these ~72 s, Private Bytes were effectively stable while working set and OS available physical memory varied. CPU-time deltas (26.0s over26.7s;43.9s over45.4s) imply about one logical processor equivalent for this process over the sampled intervals. This is derived from cumulative process CPU time and wall time, not an interval performance counter. Correlation does not establish the cause of host available-memory changes.

A separate WorkerStatus at12:23:07.539 uses health sample12:22:18.954: CPU16.99% over2.008s across12 Windows logical processors; six physical cores; host available1,963,302,912B; WSL config10GB/12 processors/2GB swap; dispatch disabled; solver process count0; scheduled tasks health producer and OF76_f3A. These health values are time-separated from the direct memory samples and are not substituted for them. The OF76_f3A task was independently observed Running/S4U with configured principal DESKTOP-K1MMENT\mksea, author blank, human initiator unknown; output path/checkpoint still unknown.

ThermalGate at12:23:18.693 accepted the five-minute time-weighted mean of seven fresh Core (Tctl/Tdie) samples:85.816C/95C, current92.625C. This is a proxy, not Core Average; fan RPM unavailable. Installed memory remains16GiB; OS-visible16,542,035,968B; difference637,833,216B, cause UNKNOWN. Preserve task/process. No setting changed, no stop/restart, no FEM dispatch. Memory gate remains held because available memory is low/variable and task recovery is unverified.

Probe source scripts/Invoke-K1WslReadOnly.ps1 SHA-256 $helperHash; pre-change backup SHA-256 $backupHash.
