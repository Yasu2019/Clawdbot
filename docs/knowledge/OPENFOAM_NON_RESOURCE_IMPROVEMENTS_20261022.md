# OpenFOAM non-resource improvement record — 2026-10-22

Linked Beads: `Clawdbot_Docker_20260125-tw5g`. Source: local source inspection and current-turn edits in `openfoam_custom`; observation date 2026-10-22 JST. This is source-level evidence only, not a successful build or run.

## Changes made

- `generalizedPolymerThermo.C`: removed the artificial `psi >= 1e-12` floor for unclipped Tait states so `psi` remains the derivative of the selected EOS; clipped states still return zero derivative. Added a tiny-`psi` regression case. Added guards for non-finite/invalid absolute pressure, temperature, shear rate, Tait denominator and non-finite outputs. Tait pVT uses `log1p` and no longer clips negative absolute pressure to zero. Cross-WLF similarly rejects invalid inputs. Cooling estimate rejects a non-finite output.
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
## Follow-up: exact low-compressibility derivative

A source audit found `boundedTaitState()` imposed `max(taitPsi, 1e-12)` in unclipped cells. That can break the EOS/derivative identity for valid low-compressibility coefficients. It now returns `taitPsi()` exactly unless density clipping is active, where the bounded density is flat and `psi=0`. Added a regression assertion using a positive coefficient producing `psi < 1e-12`. The numeric value is an analytical spot-check only; compiled test remains pending.
## C++ regression execution — 2026-10-22 17:18 JST

Environment: `opencfd/openfoam-dev:latest`, runtime reported `WM_PROJECT_VERSION=v2512`, `WM_OPTIONS=linux64GccDPInt32Opt`; container was disposable (`--rm`) with `--cpus=0.20`, `--memory=1536m`, `--memory-swap=1536m`. Inputs were bind-mounted read-only then copied into the container temporary directory. Library and test executable output went to `/tmp/of-regression`; the shared working tree was not used as a build directory. The OpenFOAM 2512 generalized-polymer-thermo library and `testThermo` compiled and linked successfully. `tests/Alltest` exited 0:

- Standard Tait derivative/state checks: 9 points, worst relative error `2.37322e-10`.
- Cooling-rate Tait derivative checks: 18 points, worst relative error `2.63089e-09`.
- Cross-WLF positivity/shear-thinning, cooling-rate transition continuity/trend, and first-mode cooling bounds/monotonicity: PASS.
- Invalid-input rejection modes: `invalidN`, `nonFinite`, `invalidVolume`, `invalidPressureVolume`, `invalidCoolingRate`, `negativeAbsolutePressure`, `negativeShearRate`, `invalidCoolingInputs`: all PASS.
- New un-clipped tiny-psi exact derivative check (`psi < 1e-12`): passed as part of standard executable.

The Ubuntu-Recovered OpenFOAM 14 attempt was not a code failure: its installed tree lacks `/opt/openfoam14/src/OpenFOAM/lnInclude/stringTemplates.C`, so wmake stopped before compilation. No file in that shared tree was modified. The successful v2512 test establishes the generalized thermo library/regression harness only. The full `polymerInterFoam` solver was not built or run; pressure/energy coupling, dynamic mesh, field conservation, restart and molding accuracy remain unverified. At 17:18:04 JST a post-test live check showed existing OpenRadioss PIDs 38422 (`-nt 12`) and 55122 (`-nt 6`) still present in `clawstack-unified-openradioss-1`; the temporary regression container had exited and was auto-removed.