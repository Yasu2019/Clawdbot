# New LAVIE WSL process visibility correction — 2026-10-31

Incident: `INC-LAVIE5500U-WSL-SOLVER-MONITOR-GAP-20261031-01`.

A Windows-only process inventory omitted active solver processes inside the WSL guest. The reviewed guest history controller now reads process names and status from guest `/proc`, records guest RAM/cgroup values separately from Windows RAM, excludes command lines, and preserves existing task schedules and solver state. Its custom-engine matcher includes `engine_k10`.

Live authenticated host readback at 2026-10-31 06:46 JST verified the installed controller SHA-256 `33E3ABB907549228743D5B2EB20C83DAA4C8156330F5ED8DA2390314E1816177` against the reviewed candidate. The normal scheduled record captured six `foamRun` ranks and one `engine_k10`; probe and guest memory status were `ok`, and command-line capture was false. The specifically reviewed stale task was already disabled and preserved. No calculation, job, checkpoint, queue or unrelated task was changed.

This confirms one telemetry sample, not job ownership, numerical validity, checkpoint recovery or sustained retention. New production dispatch remains gated by separate authorization and resolution of the installed-versus-visible RAM discrepancy.
