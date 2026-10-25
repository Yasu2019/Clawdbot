# OpenFOAM fleet readiness — 2026-10-25

Incident: INC-OPENFOAM-FLEET-READINESS-20261025-01. Observed 10:58–11:11 JST through authenticated host/solver checks.

G3: OpenFOAM Foundation 3.0.0 `interFoam` completed a fresh 2,268-cell stock water/air dam-break VOF smoke case on D and resumed natively from time 0.004 to 0.006. Periodic checkpoints at 0.002/0.004/0.006 contain alpha.water, U and p_rgh; earlier hashes remained unchanged after resume. Mesh check and normal solver termination passed. OpenFOAM 14 `foamRun` also passed environment-loaded startup checks. The first case attempt exposed a missing staged `0/alpha.water`; corrected only in the isolated copy. Source tutorial stayed unchanged.

New LAVIE: host and authenticated SSH are reachable, but a current WSL command returned Access Denied despite the registered distribution and active WSL VM. Cause remains unknown. A pre-existing LIG07 FEM task is Running; host interval CPU was 62.98% and its Tctl/Tdie sensor was 81 C at 11:11 JST. The task and WSL state were preserved; no second solver was started.

This verifies software startup and checkpoint continuation only. The water/air test does not validate resin properties, injection molding accuracy, cooling, shrinkage, voids, weld lines or short shots. No production resin case was dispatched.

Evidence is in the canonical incident note and the isolated G3 D-drive case. No credentials or raw logs are included here.