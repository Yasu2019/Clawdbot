# INC-K1MMENT-TET-FILL-JOBS-NO-RESTART-20261101-01: restart files for the tetra fill solver

Updated 2026-11-03 08:15 JST. Source: local tests and live hard-kill checks of this date.

Problem: the in-house fill solver had no restart. A power loss lost the whole run. On 2026-11-03 a planned power-off lost about 9 h 50 min. The gap had been recorded on 2026-11-01 and was not closed; new runs kept being dispatched without a recovery path.

Implemented:
- A restart file every 300 s of wall time: full solver state including trapped air, history, input fingerprint, code hash.
- Atomic write: the new file is written and fsynced under another name, then renamed. The previous file stays as the known-good copy. A torn file is skipped.
- A file of other inputs is refused, not reused. A changed code hash is logged, not refused.
- OS file locks on the run and the plan, so a second copy cannot start and a power failure leaves no stale lock.
- summary.json is written last and atomically. Restart files are removed only after it.
- A per-host task at boot and every 10 minutes starts unfinished listed plans: one start per tick, a free-RAM gate, and an alarm after 4 starts in an hour.
- The batch runner refuses a solver with no restart files unless the case opts out by name.

Verified:
- Solver level, 3 physics variants: crash and resume ends bit-identical to an uninterrupted run (arrival, pressure, source, end time, fill).
- Torn newest file falls back to the older one, with the same end result. Other inputs refused. Second process refused; lock free after release.
- Live, real mesh, process hard-killed: one Windows host resumed at step 78, one Linux host at step 123.
- Restart cap fired as designed during testing.

Not verified:
- A real reboot or power cut. The boot trigger is registered, not exercised.
- Hosts other than the two kill-tested run the same code, and restart files were seen being written, but no kill was done there.
- Runs started before this change have no restart files until they end.
- The voxel solver has no restart files; the batch runner refuses it.

Lesson: search the incident record before dispatch. A known gap stays open until a test closes it.
