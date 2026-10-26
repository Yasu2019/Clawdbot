# G3 OpenFOAM One-Off VOF Smoke Run — Sanitized Knowledge Card

Observed: 2026-10-26 (JST). One user-authorized, isolated run was executed on G3 while the existing OpenRadioss monitoring task was left enabled and unchanged.

- Solver: OpenFOAM Foundation 3.0.0 `interFoam`; stock water/air dam-break VOF tutorial, 2,268 cells, serial, one thread.
- `blockMesh`, `checkMesh` (`Mesh OK`), `setFields`, and both solver stages completed. The resumed stage reached `End` at t=0.006.
- Native fields `alpha.water`, `U`, and `p_rgh` were written at t=0.002, 0.004, and 0.006. A known-good t=0.004 checkpoint was preserved before resuming from `latestTime`; hashes remained unchanged and the resumed output has its own hashes in the restricted run manifest.
- The case is a runtime/restart smoke test only. It does not validate polymer rheology, injection molding, thermal coupling, product geometry, experimental accuracy, or defect prediction. A tiny negative `alpha.water` undershoot (~1.1e-11) appeared at the final time and is not an engineering quality metric.
- Launcher lessons: source the OpenFOAM environment before enabling Bash nounset; stage large scripts in bounded verified chunks and invoke them with a short remote command; retain immutable logs, provenance hashes, and prior checkpoints.

Canonical evidence (restricted project note and G3 run folder) records exact paths, hashes, host preflight, monitor-task status, restart procedure, and limitations. No credentials, private addresses, account identifiers, raw logs, or personal data are included in this card.
