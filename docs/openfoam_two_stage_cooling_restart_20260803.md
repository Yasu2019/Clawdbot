# OpenFOAM two-stage cooling restart rule (2026-08-03)

| Field | Record |
|---|---|
| Goal | Continue a completed thermo VOF fill as a closed-gate cooling calculation without rerunning 30 s of fine-step filling. |
| Context | minus-X Dynabook Moldflow Cool+Flow+Warp reference; OpenFOAM two-phase thermo case; MF ejection p95 8.539049 s and frozen horizon 30.000099 s; accuracy label remains `PROXY_GAP`. |
| Observed facts | The existing `resin_fill_cool` default cooling horizon was 0.5 s. The verified MF reference requires evaluation through 30.000099 s. A continuous fine-step fill/cool run would waste solver time. |
| Hypotheses | A restart with zero gate velocity and an isothermal 323.15 K gate can preserve the filled state while resolving the longer cooling history. This is not validated until compared with MF temperature and ejection KPIs. |
| Decision rule | IF a source case has independent solved `U`, `T`, `alpha.polymer`, and `p_rgh` fields plus two-phase thermophysical files, THEN copy it, restart from `latestTime`, close the gate, and cool to 30.0001 s, BECAUSE this separates the Courant-limited filling stage from the slower thermal stage without fabricating initial fields. |
| Procedure | Run `scripts/openfoam_cooling_restart_builder.py SOURCE TARGET`; inspect `cooling_restart_manifest.json`; run `checkMesh`; execute the same thermo solver; extract time-resolved temperature and frozen-front KPIs. Never overwrite `SOURCE` or an existing `TARGET`. |
| Verification | Builder tests pass; source hashes/fields remain unchanged; target gate `U=(0 0 0)`; controlDict uses `startFrom latestTime`, `endTime 30.0001`, `maxDeltaT 0.02`, `maxCo 0.5`, `maxAlphaCo 0.2`. Solver promotion additionally requires completion, boundedness, MF tolerance pass, and a repeated run. |
| Failure signatures | Missing `T`/`alpha.polymer`/`p_rgh`, missing thermophysical file, missing gate patch, target already exists, end time not later than source, solver Courant divergence, or non-monotonic cooling. |
| Recovery / rollback | Builder deletes only a newly created partial target on failure. The source is read-only. Remove a failed target only after verifying its exact path and authorization, then rebuild from the original fill case. |
| Scope limits | This builder does not prove heat-transfer coefficients, coolant conjugate heat transfer, shrinkage, sink marks, weld lines, or warpage. It does not promote `MOLDFLOW_EQUIVALENT`. |
| Next experiment | After pressure repeat r35 and worker availability, run an independent thermo fill to about 1.23 s, build the cooling restart, and compare 8.539049 s and 30.000099 s fields with MF temperature targets. |
| Provenance | `scripts/openfoam_cooling_restart_builder.py`; `scripts/test_openfoam_cooling_restart_builder.py`; Beads `Clawdbot_Docker_20260125-270e`; baseline commit `e1234b894b`. |
