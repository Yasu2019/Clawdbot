# RAM resource follow-up - BCD and display memory check

Incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01`
Observation: 2026-10-31 20:10-20:12 JST, authenticated read-only SSH to DESKTOP-K1MMENT as mksea.

Two Win32_PhysicalMemory DIMMs total 17,179,869,184 B; Windows-visible memory is 16,542,035,968 B, leaving 637,833,216 B (608.285 MiB) unexplained. Current BCD output has no truncatememory, removememory, or badmemorylist entry. AMD Radeon AdapterRAM is 536,870,912 B (512 MiB); this does not map the gap and is only a proximity clue. Cause remains UNKNOWN.

WSL config is 10 GB / 12 processors / 2 GB swap; guest at 20:11 had 10,429,976,576 B total and 9,958,612,992 B available. These values are separate from Windows available memory (11,578,404,864 B at 20:12). Production policy remains false and dispatch is held. No host/task/job/checkpoint/solver/BIOS setting changed.

Evidence: `artifacts/new-lavie/ram-bcd-gpu-live-followup-20261031-2012.md`.