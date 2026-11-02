# K1 OF76_f3A principal and admission follow-up — 2026-11-02 12:19 JST

Incident: INC-K1MMENT-OF76F3A-CHECKPOINT-OUTPUT-UNKNOWN-20261102-01; related RAM incident INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01.

Authenticated read-only OF76F3ATask at 12:19:19.204 JST and FillTaskProgressLite at 12:19:49.879 JST show task OF76_f3A still Running, LogonType S4U. The task principal SID resolved on K1 to DESKTOP-K1MMENT\mksea; task RegistrationInfo.Author is blank. This identifies the configured run-as account, not the human who registered or started the task. Task action is cmd.exe, working directory C:\m76\t; no recognized output flag, output directory, progress log, or checkpoint inventory was found. Preserve; do not stop, restart, or reuse.

Exact Python PID2196/name/start still matches (2026-11-02T02:00:12.1863044+09:00). At 12:19:49.879 it showed cumulative CPU 35,761 s, Private Bytes 13,772,988,416 B and working set 4,804,055,040 B. A prior direct sample at 12:16:56 showed CPU35,590.7 s; the cumulative-time delta over about173 s implies approximately one logical processor of average CPU for that interval (inference from samples, not a Windows interval counter). Private Bytes are not physical RAM. The previously identified ill_batch_76case.py static scan still has no direct checkpoint/restart serialization evidence; runtime recovery remains UNKNOWN.

Resource gate evidence: WorkerStatus observed 12:19:17.671 JST, based on health sample 12:18:18.199: 10.98% CPU over2.027s normalized across12 logical processors; 6 physical cores; health host available1,587,273,728 B; dispatch false; solver count0; WSL config10GB/12 processors/2GB swap. Direct MemoryCapacityNativeLite at12:19:17.775 measured host available839,069,696 B; this differs by source time (~59.6s) and must not be reconciled as a simultaneous reading. Installed16GiB vs OS-visible16,542,035,968B leaves637,833,216B unattributed.

ThermalGate at12:19:59.421 accepted a seven-sample, fresh, time-weighted trailing-five-minute Core (Tctl/Tdie) mean of87.0487 C against the existing95 C limit; current sample82.875 C. This is the documented Tctl/Tdie proxy, not Core Average. No fan RPM is exposed. Thermal pass does not clear the low/volatile memory or unknown recovery gates; no FEM dispatched and no host/task/process setting changed.

Read-only probe now resolves the exact task principal SID locally without WMI; validated on live K1. Probe source scripts/Invoke-K1WslReadOnly.ps1 SHA-256 $helperHash; pre-change backup SHA-256 $backupHash.
