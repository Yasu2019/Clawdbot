# FEM scheduler auto-resume gate near miss — 2026-11-01

An enabled periodic/boot watcher can start an OpenFOAM resume task based on solver-process presence, a pause marker, and prior run history. The watcher does not consult the separate production and dispatch authorization gates. This creates a path for an unattended restart if the pause marker disappears while the gates are still closed.

During the live review, production and dispatch remained disabled, the pause marker was present, and the next scheduled check left the case paused. No solver was restarted and no task, input, or checkpoint was changed. The exact case owner and authorization remain unconfirmed.

Keep the existing job and checkpoints intact. Before any future resume, require production approval, current host health/resource admission, explicit authorization for that case, and a verified solver-native recovery path. The watcher guard proposal is pending authorization; no change is claimed as deployed.
