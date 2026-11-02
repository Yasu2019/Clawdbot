# K1 resource and task refresh — 2026-11-02 11:41 JST

Linked incident: `INC-K1MMENT-POWER-CONTINUITY-PROBE-TIMEOUT-20261102-01`.

- Live WorkerStatus validated K1 SSH/WSL route and WSL 3.0.3.0; configured WSL memory10GB/processors12/swap2GB; FEM dispatch false; WSL solver count0. Host available RAM1.20GB; CPU15.89% over2.003s on12 logical processors; Tctl/Tdie87.125C observation-only. Cooling setting active, fan/Core Average unavailable.
- Existing scheduled task OF76_f3A reported Running under S4U; author not set and human owner unknown. Python PID2196 had 24.37GB private bytes and7.33GB working set at11:41:45. Preserve existing work; private bytes are not physical RAM consumption. No checkpoint/resume was freshly verified here.
- All8 qualification/native-proof file hashes matched expected records at11:41:58. This verifies record integrity only; no new production case was launched. Dispatch remains disabled pending RAM, recovery and production gates.
- Cause of earlier composite probe timeouts remains UNKNOWN. No task, process, solver, setting or reboot action occurred.

Canonical incident note retains exact source evidence and caveats.
