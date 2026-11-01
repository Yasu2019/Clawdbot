# FEM scheduler auto-resume gate near miss — 2026-11-01

An enabled periodic/boot watcher can start an OpenFOAM resume task based on solver-process presence, a pause marker, and prior run history. The watcher does not consult the separate production and dispatch authorization gates. This creates a path for an unattended restart if the pause marker disappears while the gates are still closed.

During the live review, production and dispatch remained disabled, the pause marker was present, and the next scheduled check left the case paused. No solver was restarted and no task, input, or checkpoint was changed. The exact case owner and authorization remain unconfirmed.

Keep the existing job and checkpoints intact. Before any future resume, require production approval, current host health/resource admission, explicit authorization for that case, and a verified solver-native recovery path.

## Sanitized implementation update — 2026-11-01

The automatic watcher path now fails closed unless production policy is enabled, health is fresh and dispatch-enabled, and a time-limited authorization exists for the exact case and checkpoint manifest. The live policy was disabled, and read-only predicate validation rejected the restart. The next scheduled watcher cycle left the case paused; no solver was restarted. Manual invocation of the separate run task remains outside this watcher-only control. This change does not authorize a calculation.

## Sanitized checkpoint-integrity update — 2026-11-01

The watcher now recomputes the live checkpoint digest and requires an exact match to the authorized time and manifest before requesting a restart. A read-only audit confirmed both the current checkpoint and a retained known-good checkpoint still match saved file hashes. The first natural post-v2 cycle completed successfully at 11:51:51 JST; status remained paused with a PAUSE marker and no OpenFOAM/MPI process. A malformed ad-hoc status probe briefly produced a false result, corrected before any action using independent readbacks. Production/dispatch remain disabled; no calculation was restarted. Direct invocation of the separate run task remains outside this watcher-only control.

A second natural post-v2 cycle also completed successfully at 12:01:01 and preserved the paused state. Review found the separate Run task launcher has a mismatched relative script path and no independent dispatch gate; no task or file was changed. A path-only repair could expose an ungated resume command, so any launcher change requires separate approval. Production/dispatch remain disabled; no calculation is authorized.

The separate Run task is Ready but idle. A read-only inventory found its relative resume-script path does not match the only observed file location. The parent resume script can remove a pause marker and start solver ranks, so path correction alone would be unsafe. The exact launcher gate/path change remains pending approval; no task, script, checkpoint, or solver changed.

A third natural post-v2 cycle completed at 12:11:11 and preserved the paused state. A fresh read at 12:12 showed production and dispatch still disabled, no solver process, and a present pause marker. No calculation was authorized or started.

The monitored host sample at 12:12:14 reported 36.94% CPU across all logical processors over about two seconds and 83.75 C from a package-level sensor; average-core and fan values were unavailable. These values do not establish long-term saturation or fan speed.
