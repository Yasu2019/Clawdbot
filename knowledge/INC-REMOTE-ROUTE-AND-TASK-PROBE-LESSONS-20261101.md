# Incident knowledge: remote route and worker-state probes (2026-11-01)

## Scope and sources
Sanitized follow-up for INC-MYOURENJI1-ROUTE-FLAG-FLUCTUATION-20261101-01 and INC-K1MMENT-OF76-UNEXPECTED-RUNNING-20261101-01. Evidence was captured during live checks on 2026-11-01 JST and retained in authorized local incident records. This note omits device addresses, account names, local paths, credentials, and raw logs.

## Verified observations

- A tailnet peer reported Offline, and the session browser-control host was unavailable. Those observations established that these access routes could not control the target from this session. The target power state, Windows sign-in state, and any separate user-side Remote Desktop session remained unknown.
- Two scheduled batch tasks remained Running. Their task actions and process ancestry showed active custom Python fill workers, not OpenFOAM/OpenRadioss/CalculiX/Elmer processes. Each child accrued about 2.94 CPU seconds during a 3-second sample and held about 1.9 GiB working set. The human starter and authorization were unknown.
- Batch wrapper logs were empty and child logs had not been updated for several minutes. CPU counters continued to rise, so old log timestamps and one empty filtered process query did not establish a stall. Why the filtered query missed the process tree remains unknown; a later PID/parent query found both trees.
- A separate historical OpenFOAM native-restart validation was rehashed using its manifest: 17/17 checks matched for the first checkpoint fields, retained known-good field files, mesh provenance, and resumed endpoint. This proof does not cover the two live Python fill jobs.

## Controls to prevent recurrence

1. Classify network, monitoring, worker, requested application, and visible desktop routes independently. A failed VPN/tailnet or browser route is not proof that a PC is powered off or at its sign-in screen. Claim GUI control only with live screen evidence.
2. Before declaring a scheduled job absent, stalled, or safe to restart, reconcile Task Scheduler state/action, process names and PID parentage, CPU deltas over a timed interval, output timestamps, and checkpoint evidence. A narrow filter returning no matches is insufficient.
3. Treat stale logs as an uncertainty signal; use a fresh process/resource sample and solver-native progress/checkpoint readback before acting. Preserve unrelated work when owner, authorization, or recovery path is unknown.
4. Verify restart files at the exact manifest-declared paths, including a retained known-good checkpoint and mesh/input provenance. Keep solver restart proof separate from unrelated custom Python workloads.

## Status and limits

No tasks, processes, host settings, or solver runs were changed. New FEM dispatch remained held pending ownership/recovery and host RAM reconciliation. The exact cause of the process-query miss, the route outage, the human task starter, and the target sign-in state remain unknown. No FMEA score or formal priority was assigned.

## Resource-measurement correction (2026-11-01 JST)
A live Windows sample found 16 GiB installed across two DIMMs using Win32_PhysicalMemory, 15.41 GiB visible through Win32_OperatingSystem, 6.53 GiB free, and a 637,833,216-byte installed-to-visible gap of unknown cause. An earlier report mislabeled Win32_ComputerSystem.TotalPhysicalMemory as DIMM-installed capacity; it returned the OS-visible value. Use the direct DIMM inventory for installed RAM, the OS for visible/free memory, and report unresolved gaps without changing BIOS/WSL from the mismatch alone. A material unexplained gap remains a FEM dispatch hold.

## Shared Beads hook effect (2026-11-01 JST)
A single-file commit from a dedicated worktree can still run a configured post-commit hook that exports the full Beads issue/memory snapshot into a shared worktree. After each such commit, inspect the hook target's status and hash; never assume the worktree isolates hook writes. Preserve any generated staged data and keep it out of the incident-only commit unless separately reviewed. Here the export was not pushed; the exact prior dataset diff was unknown because no complete pre-commit baseline existed.
