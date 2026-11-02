# K1 RAM probe timeout and memory reconciliation ? 2026-11-02 15:50?15:58 JST

Incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01`.

- SMBIOS and installed-memory API independently report16 GiB installed; Windows/PSAPI visible capacity16,542,035,968 B; difference637,833,216 B persists. Radeon registry value512 MiB is correlation only; BCD has no explicit memory cap. Cause UNKNOWN.
- Windows available physical:8,858,236 KiB / PSAPI8,894,353,408 B at15:52:36; system commit19,360,743,424/22,313,713,664 B. WSL guest availability9,921,380,352 B of10,429,976,576 B at15:52:44; keep host and guest separate.
- `MemoryCapacityNativeLite` timed out again. Exact audit found two childless mksea PowerShell shells with the fixed SSH bootstrap (56,758,272 B and56,672,256 B working sets); both were stopped only after exact PID/start/account/parent/hash verification and verified absent. No calculation/task/data targeted. Helper now has a fixed identity-audit/cleanup guard; raw command lines stayed private.
- At15:58:36, two existing custom fill workers continue. PID19700 step580/fill0.999 has a WMI/Get-Process Private Bytes disagreement of2,410,131,456 B; cause unknown. PID14580 step420/fill0.987; memory sources agree. Both tasks Running/mksea/S4U; preserve.
- Disable this repeated timeout-prone probe pending review. Dispatch remains held for unexplained installed-visible gap, RAM/case budget, restart evidence and separate production authorization. No host configuration or solver/job change.

16:02 follow-up: local route-classification omission on the first new audit was corrected; no remote change. Fixed exact audit verified two childless agent-owned shells stopped and all four PIDs absent. MemoryCapacityNativeLite was removed from the caller allowlist after repeat timeouts. PageFileStatus/WSL values remain separate; latest thermal gate is Tctl/Tdie mean92.2288C/8 samples, instant91.5C, not Core Average. Capacity gap remains UNKNOWN; dispatch held.
Graphify: three exact-ID nodes/six links added after a first atomic write aborted on two pre-existing unrelated dangling links (preserved, not repaired). New endpoint validation passed; explain/path retrieval passed. See linked graph evidence.

16:09 JST: host/guest availability and commit measured separately; installed-visible gap remains unresolved. Tctl/Tdie rolling5m mean92.8159C/7 samples, instant93.125C; Core Average/fan unavailable. Dispatch remains held.

16:09 JST Graphify refresh: added exact nodes `k1_ram_resource_status_20261102_1609` and `k1_of76_live_status_20261102_1609` with six validated links; `graphify explain` and path to the dispatch hold passed. Two pre-existing unrelated dangling links remain preserved. Graph SHA-256 `38831e60ef485dd91acadde1cc41e9c5ae90274d11491ea2918b73234e127824`.
