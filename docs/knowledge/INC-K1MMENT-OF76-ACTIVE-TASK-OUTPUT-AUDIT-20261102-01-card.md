# K1 active fill tasks: unknown ownership and restart status

Observed 2026-11-02 15:24-15:28 JST from authenticated read-only K10 probes to DESKTOP-K1MMENT. Two OF76 custom fill tasks were Running under the Windows worker account with S4U logon; registered authors and human initiators are unknown. Two Python workers had 24 threads each and were writing progress logs. Their outputs show progress, but are not verified solver runs. The standard solver counter was zero and dispatch remained disabled.

Top-level metadata inventories of the exact output folders found only `log.txt`; no checkpoint filename candidates were found. The inventories were nonrecursive, so a checkpoint elsewhere is not ruled out. A worker-specific checkpoint query pinned to an old PID failed; cause unknown. Both existing jobs and their files were preserved. Do not stop, reuse, or resume them without owner intent and a verified recovery path. Hold new FEM dispatch pending ownership, checkpoint, case RAM, and separate production authorization.

Thermal snapshot: 5-minute time-weighted LHM `Core (Tctl/Tdie)` mean 83.53 C, instantaneous 94.25 C. Core Average and fan values were unavailable. The configured gate accepted its temperature test; that is not a production authorization. Host CPU was 18.49% across 12 logical processors and OS available memory 9,143,083,008 bytes at the associated live snapshot; these are host-wide observations, not available job capacity.

Related incident: `INC-K1MMENT-OF76-ACTIVE-TASK-OUTPUT-AUDIT-20261102-01.md`. Helper `scripts/Invoke-K1WslReadOnly.ps1` added fixed task/output metadata probes; it does not change remote tasks or files.
## Follow-up 2026-11-02 15:36-15:38 JST
Both tasks remain Running and two Python workers advanced logs (N1 step340; B step140). A third output directory now contains fields/history/log/summary files, but completion is unknown. Three exact top-level inventories found no checkpoint-name candidates; search was nonrecursive. PID14580 memory readings differ: WMI Private Bytes3,397,689,344 B vs Get-Process2,404,704,256 B; cause unknown. Thermal gate mean92.56 C/7 samples, instantaneous92.125 C; dispatch remains disabled. Preserve all work; no resume/new FEM authorization.

Memory telemetry follow-up 15:37:56 JST: second FillWorkers sample reproduced PID14580's WMI/Get-Process Private Bytes discrepancy (3,397,689,344 vs2,404,704,256 B); source freshness/cause unknown; retain both values.
