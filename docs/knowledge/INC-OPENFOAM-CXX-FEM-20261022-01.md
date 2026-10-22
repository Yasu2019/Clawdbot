# OpenFOAM build and FEM admission incident — 2026-10-22

Incident: `INC-OPENFOAM-CXX-FEM-20261022-01`. This card contains reviewed, sanitized findings only; raw event logs, process IDs, user paths and credentials are excluded.

## Verified work

- OpenFOAM v2512 generalized thermo C++ regression passed earlier in a resource-capped disposable build.
- A later isolated source build compiled and linked the current `polymerInterFoam` executable and generalized thermo library after correcting an internal-field type mismatch in the temperature equation.
- The full build was not verified. The dynamic-mesh target failed to resolve custom VoF includes because its make options pointed one directory too high. The source include path was corrected; the correction still requires a clean rebuild.
- Dynamic-mesh polymer thermo/energy coupling remains generic and is not validated for molding predictions.
- No new FEM case was dispatched and no solver result was produced.

## Admission incident

At 2026-10-22 19:18 JST, the local Windows host reported 47.77 GiB visible RAM and 6.10 GiB available. The Docker Desktop WSL guest reported only about 50 MiB available and load average 82.95 on 20 logical CPUs, with two pre-existing OpenRadioss calculations still active. The host Docker CLI returned HTTP 500 while the WSL daemon process remained present. The Docker/API fault cause is **UNKNOWN**. No existing calculation, checkpoint or scheduled task was stopped or overwritten. New build/FEM dispatch remains held pending fresh host/guest/worker/queue/checkpoint checks and the user's exact cleanup decision.

## Controls and follow-up

- Clean only generated architecture-specific dependency directories inside a disposable build copy; preserve source make files.
- Require full main and dynamic solver build, regression, solver/case provenance, native checkpoint and exact resume procedure before unattended FEM.
- Before stopping any older calculation, identify its recovery mechanism and known-good checkpoint, obtain confirmation for the exact target, then verify unrelated work remains intact.
- FMEA/FTA/QC process chart/Control Plan are linked to the incident in the local canonical note; numeric risk ratings and acceptance thresholds remain unassessed.

Canonical local evidence: `docs/knowledge/INC-OPENFOAM-CXX-FEM-20261022-01.md`.
