# FEM scheduler auto-resume gate near miss — 2026-11-01

An enabled periodic/boot watcher can start an OpenFOAM resume task based on solver-process presence, a pause marker, and prior run history. The watcher does not consult the separate production and dispatch authorization gates. This creates a path for an unattended restart if the pause marker disappears while the gates are still closed.

During the live review, production and dispatch remained disabled, the pause marker was present, and the next scheduled check left the case paused. No solver was restarted and no task, input, or checkpoint was changed. The exact case owner and authorization remain unconfirmed.

Keep the existing job and checkpoints intact. Before any future resume, require production approval, current host health/resource admission, explicit authorization for that case, and a verified solver-native recovery path.

## Sanitized implementation update — 2026-11-01

The automatic watcher path now fails closed unless production policy is enabled, health is fresh and dispatch-enabled, and a time-limited authorization exists for the exact case and checkpoint manifest. The live policy was disabled, and read-only predicate validation rejected the restart. The next scheduled watcher cycle left the case paused; no solver was restarted. Manual invocation of the separate run task remains outside this watcher-only control. This change does not authorize a calculation.

## Sanitized checkpoint-integrity update — 2026-11-01

The watcher now recomputes the live checkpoint digest and requires an exact match to the authorized time and manifest before requesting a restart. A read-only audit confirmed both the current checkpoint and a retained known-good checkpoint still match saved file hashes. The first natural post-v2 cycle completed successfully at 11:51:51 JST; status remained paused with a PAUSE marker and no OpenFOAM/MPI process. A malformed ad-hoc status probe briefly produced a false result, corrected before any action using independent readbacks. Production/dispatch remain disabled; no calculation was restarted. Direct invocation of the separate run task remains outside this watcher-only control.
