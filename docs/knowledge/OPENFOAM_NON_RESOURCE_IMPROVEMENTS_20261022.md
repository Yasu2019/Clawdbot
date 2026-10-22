# OpenFOAM non-resource improvement record — 2026-10-22

Linked Beads: `Clawdbot_Docker_20260125-tw5g`. Source: local source inspection and current-turn edits in `openfoam_custom`; observation date 2026-10-22 JST. This is source-level evidence only, not a successful build or run.

## Changes made

- `generalizedPolymerThermo.C`: added guards for non-finite/invalid absolute pressure, temperature, shear rate, Tait denominator and non-finite outputs. Tait pVT uses `log1p` and no longer clips negative absolute pressure to zero. Cross-WLF similarly rejects invalid inputs. Cooling estimate rejects a non-finite output.
- `polymerInterFoam/TEqn.H`: added the compressible pressure/kinetic-work structure (`divUp + ddt(rho,K) + div(rhoPhi,K) - contErr*K`) weighted by phase `alpha/Cv`; removed an extra post-solve thermal blend that imposed an undocumented time scale. `fvOptions.correct(T)` now precedes physical-temperature bounds.
- `generalizedPolymerThermo/tests`: added negative pressure/shear-rate and invalid-cooling failure cases, plus cooling initial/monotonic/bounds checks.
- README now states the current integration scope and explicitly says the staged 2026-09-08 binary does not validate later source; the cooling model remains a screening estimate.

## Verification and limits

- `bash -n` on `generalizedPolymerThermo/tests/Alltest`: passed.
- `git diff --check` on the touched OpenFOAM files: passed.
- C++ compile, compiled regression harness, solver run, energy balance, numerical result and restart were not tested. No solver was dispatched.
- Official OpenCFD v2512 `compressibleInterFoam/TEqn.H` was used as a structural reference for pressure/kinetic work: https://api.openfoam.com/2512/multiphase_2compressibleInterFoam_2TEqn_8H_source.html . This does not validate this polymer adaptation.
- Dynamic-mesh gap confirmed by source inspection: `compressibleInterDyMFoam.C` uses generic mixture `thermo1/thermo2` `psi1/psi2`; it does not include `generalizedPolymerThermo.H` or custom Tait/Cross-WLF updates. Do not claim custom polymer dynamic-mesh coupling is implemented.
- Remaining physics gaps: grade-calibrated viscosity/thermal coefficients, calibrated viscous dissipation, latent heat/crystallization, cooling-channel/runner boundary coupling, mesh-motion conservation and field feedback validation.

## FMEA / FTA / QC / Control Plan draft

Linked ID: `Clawdbot_Docker_20260125-tw5g`; qualitative and unscored.

- FMEA failure mode: source feature or test is mistaken for validated solver behavior. Effect: invalid molding predictions. Evidence/cause: current source differs from staged binary; no current-source compile/run. Prevention/detection: bind source and binary hashes, build version, test/run log, case provenance and restart evidence. Owner unassigned; validation pending; residual risk high/unassessed.
- FTA top event: custom polymer prediction is materially wrong. OR branches: uncompiled source, generic dynamic-mesh thermo, uncalibrated grade coefficients, omitted/calibrated-later energy terms, missing matched validation case. Branches remain separate evidence states; no single root cause asserted.
- QC process chart gate: before using any result, require successful current-source build, regression tests, conservation/energy checks, static and moving mesh matched case, and checkpoint provenance. Numeric acceptance limits are not established here.
- Control Plan: characteristic = solver release/result provenance; method = each source change/build/run; acceptance limits pending validated criteria; reaction = mark unverified and do not use as production result; owner unassigned; effectiveness not established.

No solver process, task, binary, checkpoint or unrelated work was modified.