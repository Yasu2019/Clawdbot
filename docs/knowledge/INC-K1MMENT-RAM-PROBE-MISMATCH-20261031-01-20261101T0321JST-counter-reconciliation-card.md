# RAM counter reconciliation follow-up — 2026-11-01 03:20–03:21 JST

Incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01` (cause remains UNKNOWN)

## Live evidence and interpretation

- Authenticated SSH to the recognized New Red LAVIE host confirmed computer name `DESKTOP-K1MMENT` at 2026-11-01 03:20 JST; the Tailscale route also answered live.
- At 03:20:28 JST, SMBIOS/CIM listed two Hynix DDR4-3200 DIMMs, 8 GiB each (17,179,869,184 B installed). Windows-visible memory was 16,542,035,968 B (15.4 GiB); the 637,833,216-B (608.285 MiB) gap remains unexplained. AMD Radeon `AdapterRAM` was 536,870,912 B (512 MiB), leaving 100,962,304 B (96.25 MiB) after simple subtraction; this does not establish firmware/UMA ownership.
- The 03:20:28 `Win32_OperatingSystem.FreePhysicalMemory` sample was 775,176 KiB (~757 MiB). At 03:20:40, the PerfOS memory counter reported 8,706 MiB available, 13,871,067,136 B committed of 19,092,172,800 B limit, and 370 pages/sec. At 03:20:57, Win32_OperatingSystem reported 7,865,286,656 B free; PerfOS reported 7,842,131,968 B available and 13,876,477,952 B committed, while `Get-Counter` reported 7,376 MiB and PagesPersec was 0. The later sources were close but not identical; the earlier free-memory sample diverged sharply. Cause of the short-lived disagreement is UNKNOWN. Do not use the single 03:20:28 reading as current headroom.
- At 03:20:57 a pre-existing Windows Python worker remained active; working set was 3,675.7 MiB and private bytes 8,460,935,168 B, up from a 1,779,941,376-B working set at 03:20:28. Its human initiator is not established. Preserve it; do not stop, reuse or supersede it. The WSL VM process working set was 883,560,448 B. Do not add guest available RAM to host available RAM.
- At 03:21:49 JST, the exact `Clawstack_Lavie5500U_FEM_LIG07_Practical_20261025` task was live-read as `Disabled`. No solver process was identified by the bounded Windows process-name/command-line probe. This does not prove all FEM queues are empty. No task, job, checkpoint, solver, BIOS, boot, memory-limit, or cooling setting was changed; no calculation was dispatched.

## Corrective control

For each pre-dispatch resource gate, collect installed DIMMs, Windows-visible bytes, Win32 OS free bytes, PerfOS AvailableBytes/AvailableMBytes and commit, plus active high-memory processes in one timestamped sample. Record source and sample time; do not infer headroom from one counter. Capture WSL guest memory separately. Hold new FEM dispatch while the installed/visible gap is unexplained and when the sampled resource sources conflict enough to change a job decision. Recheck the active worker and recovery state before any future allocation.

## Limits and open items

The exact physical/firmware reservation for the 637,833,216-B installed-to-visible gap is still UNKNOWN. No conclusion is drawn from `AdapterRAM` alone. A transient 0.75-GiB FreePhysicalMemory result was not reproduced by the next two PerfOS samples, but its cause has not been established. Production authorization and case-specific memory/checkpoint gates remain separate; no FEM dispatch is authorized by this note.