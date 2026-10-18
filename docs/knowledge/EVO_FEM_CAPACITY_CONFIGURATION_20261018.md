# EVO FEM capacity and runtime configuration — 2026-10-18

Beads: Clawdbot_Docker_20260125-0vae. User requested full utilization for OpenFOAM/OpenRadioss and related FEM. Configuration and validation completed without a Windows reboot.

## Applied settings and live evidence

- GPU reservation remains4GiB; Windows-visibleRAM59.65GiB (prior verified hardware reconciliation).
- C:/Users/Suzuki/.wslconfig changed20GB->48GB memory and24->32 logicalCPUs; swap8GB retained. Original preserved at C:/ProgramData/Clawstack/EvoFemCapacity-20261018/wslconfig.before. Live22:50:05 JST:32 onlineCPUs, MemTotal49,329,336KiB (~47.04GiB usable; configured upperlimit48GB is not the same as usable/freeRAM).
- Windows power changed Balanced->HighPerformance, GUIDcfea7068-2669-44d7-a4b4-740a8ce6af56. AC/DC CPUmin5%, max100%, boostmode2(Aggressive), coolingpolicy1(Active), hybridSleepoff and automaticSleep/Hibernatetimeouts0. Readback22:54 confirms values. Original power scheme exported to power.before.pow. This is OS active cooling; fixed100% fan RPM or firmware turbo mode is NOT verified or claimed.
- sshd/Tailscale Running/Automatic, TailscaleForceDaemon=true/WantRunning=true directly verified22:54:54 JST.

## Existing work protection and WSL restart

Inspected active processes, task families, queues, services, oldlocks and running distributions. Four historical Windows inboxZIPs and older job/ownerlocks were preserved; no legacy tasks/claims were cleared or reused. They are not evidence of currently executing solver work. Only the FEM distro was running; by shutdown preparation it had already idled off after solver exit. Enumeration accepts zero or exactly the authorized distro and refuses other running distributions.

P43 nt12/MPI1 andP44 nt6/MPI1 stopped using native /CHKPT+/STOP, with NORMAL TERMINATION/USERBREAK proof. Fresh checkpoint/input/binary hashes and copies verified at /srv/evo-hpc/fem-capacity-maintenance-20261018/{P1r43f,P1r44f}; original known-good0/1 and previous GPUmaintenance copies preserved. Native stop points: P43cycle33210/T0.0001078115; P44cycle19850/T0.00002151111.

After verified stops only, wsl --shutdown applied the new VM capacity. Windows was not rebooted. Dedicated manualS4U tasks Clawstack_EvoFEMCapacity_Resume_P1r43f_20261018 / P1r44f_20261018 validate expected host/GPU/guest capacity, checkpoint/input/binary hashes, sameMPI/thread layout and absence of an existing engine before resuming CHECK_DATA. ExecutionTimeLimitPT0S and IgnoreNew. They do not forcekill a calculation or retry unknown native errors.

Direct22:54:05 JST logs: P43cycle34800/T0.00010940 andP44cycle20900/T0.000022561. Both progressed beyond savedpoint; tasksRunning. This proves continuity, not scientific completion.

## Runtime tools and resource budget

- /usr/local/bin/evo-fem-preflight -> /opt/evo-hpc/fem-admission-20261018.py, policy /opt/evo-hpc/fem-policy-20261018.json.
- Live admission check uses procfs and WindowsCIM. Total configured solver-thread budget28 out of32 logicalCPUs; guest reserve4GiB, Windows freeRAM reserve6GiB, physical backing disk free-space reserve50GiB. Existing cases have explicit8GiB planned peak budgets each; exceeding a planned budget blocks additions and requires reassessment, it does not kill the process. No global9GiB RSS kill threshold.
- Unknown live solvers, unavailable host telemetry and oversubscription reject additional admission. Host and guest availableRAM are not summed. This is an explicit preflight tool/policy, not a claim that every legacy dispatcher was patched or that an automatic global scheduler is running. Legacylocks remain intact.
- At22:53:14 JST: active18 solverthreads, remaining10; requested4threads/12GiB fit, backingCfree782GiB. Resource fit alone never qualifies a production case: native checkpoint, input/run provenance and exactresume procedure must be separately validated.
- New job data root /srv/evo-hpc/fem-jobs-20261018 (nativeext4, ownerevofoam). Keep intensive solver I/O off /mnt/c. Host telemetry/report mirrors can use Windows paths; native state remains authoritative.
- Source /opt/evo-hpc/evo-fem-env-20261018.sh explicitly for new jobs. Includes OpenFOAMenvironment, preCICE/Radioss librarypaths, OMP_DYNAMIC=FALSE, OpenBLAS/MKL/NumExpr1thread and current-shell filedescriptorlimit65535. Set solver/MPI/OMP layout per case; never multiply all pools to32 independently.
- No verified complete physical-core temperature average is available in this setup. It is reported null; package/max values are not relabeled as core averages. Firmware thermal protections retained; no undervolt/PPT/unverifiedfan register changes.

Example read-only budget check:
`evo-fem-preflight --request-threads 4 --request-peak-gib 12`

## Solver validation

OpenFOAMv2512, OpenMPI4.1.6, CalculiX2.21, Elmer26.2, Gmsh4.12.1, preCICE3.4.1 and matched OpenRadiossbinary directly queried. Shared-library checks pass for ccx/ccx_preCICE/Elmer/Gmsh/Radioss and OpenFOAMpreCICEadapter when the FEMenvironment is sourced. The adapter's apparent missing FOAMlibraries in an unsourced shell was resolved by supplying the explicit environment, without changing shared binaries.

OpenFOAM: new bounded2MPI-rank icoFoam cavity roundtrip passed22:51:07 JST. Writes0.01/0.02, hashes+preserves rankfieldsU/p/phi and full0.02folders, resumes latestTime to0.04 with samebinary/partition/OMP1. Old0.02 files unchanged and known-good retained. Exact proof: /srv/evo-hpc/fem-capacity-maintenance-20261018/openfoam-restart-validation/restart-verified.json. This is a functional restart test, not a large production CFDbenchmark or coupled-case qualification.

For long production OpenFOAM runs choose a case-appropriate wall-clock checkpoint cadence (for example writeControl clockTime / writeInterval600), startFromlatestTime and preserve a verified checkpoint copy. Verify every required field on every MPIpartition and mesh/version/layout compatibility; do not blindly apply the cavity fieldset to multiphase/thermal cases. Elmer/CalculiX/coupled production runs likewise require their own verified native recovery procedure; installed adapterlibraries are not proof of coupled restart compatibility.

Windows ParaView6.2.0 pvpython import/GetParaViewVersion actual invocation passed, returning(6,2). Six admission regression tests passed, covering CPUoversubscription, missing telemetry, no double-counting RAM, unknown olderwork and avoiding fixedRSS kill policies.

## Storage and recovery

K10 externalHDD inventory22:52:31 JST: HBUFFALO WD-WX12D81HHE17 / volumeba3e629c-926b-4e5c-88e0-7ebab39bb1d2 healthy/free241.6GiB; GLogitec free134.6GiB; FTOSHIBA free11GiB. New preferred archive H:/ClawstackArchive/EVO-FEM-20261018 passed write/read/hash probe; only the operation's own probe was removed. Existing backup data unchanged. Registereddestination is on controllerK10, not a mounted localEVOdrive. Refresh identity/health/reservations/freecapacity on all3 before transfer; use GoogleDrive only if all unsuitable. Copy completed stableoutputs and verifyhashes; no automatic source deletion. No live calculation data moved.

Rollback or future capacity changes: take a NEW native checkpoint and immutable proof first; preserve current known-good, stop only owned solver processes gracefully, inspect other distributions before WSLshutdown, then restore backed-up config/power if required and verify live state. Do not rerun an old maintenanceattempt or clear unknown locks.

Evidence: D:/Clawdbot_Docker_20260119/artifacts/evo-fem-capacity-20261018/{settings-prepared,checkpoint-state,fem-policy-20261018,restart-verified,admission-live}.json.
References: https://learn.microsoft.com/en-us/windows/wsl/wsl-config (liveconsulted2026-10-18); installed solver libraries/native execution logs.