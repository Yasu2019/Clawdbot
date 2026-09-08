# INC-OPENFOAM-035: box-round-hole polymerInterFoam resume held after numerical and unit failures

Date: 2026-09-08 JST  
Beads: `Clawdbot_Docker_20260125-vq3w`  
Status: `FAILED_NUMERICS / HOLD`  

## Goal and scope

Recover the interrupted `polymer_coupled_case_l5` calculation without changing completed CalculiX or Elmer results and without stopping unrelated watchdogs or scheduled tasks. The original case remains immutable. This work does not validate material, process, filling, or structural conclusions.

## Observed facts

- Original solver: OpenFOAM 2512 custom `polymerInterFoam`.
- Original mesh: 24,891 cells; `checkMesh` passed, but its bounding box was `(0 0 0)` to `(100 60 50)` in OpenFOAM SI coordinates while the canonical specification says `100 x 60 x 50 mm`.
- Original log stopped at `Time = 4.1702571` after maximum Courant number rose to `275483.11`, `deltaT` fell to `8.8494149e-23 s`, the T solve residual reached `4.1953141e+32`, and SIGFPE occurred.
- Every written original checkpoint after `0.05 s` was already invalid for continuation. At `0.05 s`, `max |U| = 1868.71 m/s`; at `4.15 s`, `max |U| = 2119.80 m/s`, `max T = 1124.57 K`, and `max p_rgh = 33.07 MPa`.
- CalculiX `calculix_coupling_l1/ccx.log` contains `Job finished`.
- Elmer `elmer_coupling_l1/elmer.log` contains `ALL DONE`.
- Copy verification for `polymer_coupled_case_l5_resume_r1`: 3,523 files and 646,365,845 bytes on both sides; sampled SHA-256 hashes matched.
- SI-scaled R2 mesh bounding box is `(0 0 0)` to `(0.1 0.06 0.05) m`; total volume is `4.1326733e-05 m3`; `Mesh OK`.

## Three bounded recovery trials

| Trial | Single controlled change | Result |
|---|---|---|
| R2 | SI scale plus consistent vent pressure `101325 Pa` | Completed `0.01 s` in 224 s; `max |U|=1.9603 m/s`, alpha `[0,1]`, but `max T=984.76 K`; execution only, numerically/physically rejected. |
| R3 | Disable uncalibrated energy source terms; bounded upwind T advection; clamp T to `[313.15,503.15] K` | No FPE, but localized Courant control reduced `deltaT` to `8.31e-08 s` at `t=2.58e-04 s`; stopped under bounded retry/no-waste rule. |
| R4 | Set surface tension to zero as one-variable diagnostic | Same `deltaT` collapse (`8.24e-08 s` near the same time); surface-tension hypothesis rejected; stopped. |

## Root-cause analysis (5 Why)

1. Why did the original solver stop? A local velocity/temperature excursion drove Courant number and the T equation beyond floating-point range.
2. Why were velocities already extreme at the first saved step? Geometry coordinates were treated as metres instead of millimetres and the vent pressure datum was `0 Pa` while the interior/thermodynamic pressure datum was approximately `101325 Pa`.
3. Why could the checkpoint not be reused? The first saved checkpoint already contained `|U| > 1800 m/s`; all later states inherited that corruption. A stale pre-existing time directory named `5` also makes blind `latestTime` unsafe.
4. Why did the SI/pressure repair still fail the thermal gate? The custom energy equation retained an uncalibrated kinetic-energy coupling and relied on hard clamps, producing `984.76 K` in `0.01 s` despite inlet/mould temperatures of `503.15/313.15 K`.
5. Why is full continuation still held after bounding energy? The custom solver computes `etaCrossWLF` and a relaxed Tait density, but the evidence does not yet prove a stable, conservative coupling of those fields into momentum/pressure/energy. The remaining localized Courant collapse needs a solver-level minimal benchmark, not further blind case tuning.

## Fishbone / logical tree

- Units: millimetre geometry entered an SI solver without scaling.
- Boundary conditions: absolute and gauge pressure conventions were mixed.
- Model implementation: Cross-WLF/Tait/energy coupling is incomplete and uncalibrated.
- Numerics: initial discontinuities and pressure-density correction generate a localized high-speed cell.
- Workflow: existence of a time directory was treated as resumability; no field-bound gate rejected corrupted checkpoints.
- Validation: material grade and process conditions remain missing, so engineering validation is impossible.

## FMEA

| Failure mode | Effect | S/O/D | Countermeasure |
|---|---|---:|---|
| mm mesh interpreted as m | Wrong volume, time scale, Reynolds/Capillary response | 10/6/3 | Assert mesh bbox against canonical dimensions before solver start. |
| Mixed pressure datum | Large artificial pressure gradient and velocity | 9/5/4 | Assert `p`, `p_rgh`, `pMin`, inlet and vent datum consistency. |
| Corrupted checkpoint accepted | Repeat divergence or silently invalid result | 9/7/5 | Gate restart on bounded U/T/p/alpha and reject stale/non-monotonic time directories. |
| Incomplete thermo-rheology coupling | Nonphysical temperature/density/viscosity | 10/7/7 | Validate each coupling on an analytical/minimal benchmark before the full cavity. |
| Blind repeated tuning | Wasted compute and false confidence | 7/6/3 | Three bounded attempts maximum; then HOLD with evidence. |

## Decision rules

- IF the OpenFOAM bbox differs from the specification after unit conversion, THEN do not launch the solver, BECAUSE `checkMesh: Mesh OK` does not validate units.
- IF any candidate restart state exceeds declared U/T/p/alpha physical bounds, THEN reject the checkpoint and start an isolated generation from clean inputs.
- IF an energy model requires a clamp to remain within inlet/wall temperatures without a calibrated heat source, THEN classify it `FAILED_NUMERICS`, not a thermal result.
- IF three bounded repair trials fail to meet the smoke gates, THEN stop and isolate a minimal solver benchmark before further full-case trials.

## Recovery / rollback

- Original case: `artifacts/box_roundhole_v5/polymer_coupled_case_l5/` (untouched).
- Backup branch: `backup/openfoam-resume-20260908_060102` at commit `7d220fa6ddbcd12df2cfe2fc74102f2b38900b03`.
- Previous solver binary: `openfoam_custom/bin/polymerInterFoam.pre_inc_20260908_061538` (timestamp suffix is authoritative if it differs by seconds).
- Diagnostic generations R1-R4 are preserved; no completed CalculiX/Elmer outputs were modified.

## Verification and next experiment

Before another full-cavity launch, create a small SI two-phase channel benchmark with the same solver and require:

1. exact pressure-datum consistency;
2. alpha within `[0,1]`;
3. temperature within declared energy-balance bounds without relying on a clipping event;
4. mass imbalance <= 2%;
5. bounded velocity consistent with the imposed `0.05 m/s` inlet;
6. timestep not collapsing by more than 100x over the smoke interval;
7. repeatability from clean inputs.

Only after this passes should the fixed implementation be applied to a new full-cavity generation. No result from R1-R4 is validated engineering evidence.

## Web-search decision

No web search was used. The failure was resolved to local first-party evidence (mesh bounds, canonical spec, source, logs, and controlled A/B trials); external advice would not replace the missing minimal conservation benchmark or material calibration.

## HOLD-release benchmark attempt (2026-09-08)

The user approved proceeding while preserving the pre-existing
`ClawstackVivobookOpenFOAMResume` watchdog. It remained running and was not
stopped, disabled, deleted, or reused. The benchmark ran independently on K10.

- Setup R1: `0.02 x 0.002 x 0.001 m`, 160 cells. Solver ended normally at
  `0.002 s`, but the outlet had not reached flow-through equilibrium, so the
  mass-balance gate was not evaluable.
- Candidate R2/R3: `0.001 x 0.002 x 0.001 m`, 80 cells, `0.04 s`. The final
  inlet/outlet volume flux magnitudes both reached `1.0e-7 m3/s`, velocity
  reached the imposed `0.05 m/s`, alpha stayed within `[0,1]`, temperature was
  `503.15 K`, maximum Courant number was approximately `0.010001`, and the
  timestep grew from `1.200012e-6` to `1.000062645e-5 s` without collapse.
- Rejection: R3 logged 1,099 linear solves that reached the configured maximum
  of 1,000 iterations. This is not a clean solver repetition and does not prove
  the required no-clipping energy behavior. A second acceptance repetition was
  therefore not run.

Decision: the HOLD is **not released**. The next bounded change must expose and
count temperature-clipping events and correct the pressure/temperature linear
solver convergence before two clean repetitions are attempted.

## Conditional release and full-geometry recheck

The solver was instrumented to report every temperature bound event. Removing
the relaxed Tait `rho` overwrite was tested but did not eliminate the small-case
temperature excursion, so that inconclusive source change was reverted. Small-
case p/T solvers used PCG/DIC and PBiCGStab/DILU respectively. The energy bound
uses a `1e-6 K` comparison tolerance and records an event before applying the
safety bound.

Two clean independent minimal runs (`r13_pass_a`, `r14_pass_b`) at an interior
test temperature of `500 K` passed identically:

- normal `End`, no NaN/FATAL, no 200/1000-iteration cap;
- zero `temperatureBound event` occurrences;
- final inlet/outlet flux magnitudes both `1.0e-7 m3/s` (0% imbalance);
- sampled maximum velocity `0.050864123326 m/s` for a `0.05 m/s` inlet;
- final `T=500 K`, alpha within `[0,1]`, max Courant bounded;
- timestep increased from `1.200012e-6` to `1.000062645e-5 s`;
- final U/T/alpha/p_rgh SHA-256 hashes matched between repetitions.

This released only the gate for an isolated full-geometry smoke generation.
It did not authorize reuse of the corrupted original checkpoints.

Full-geometry `r5_conservative` advanced beyond the former collapse point to
`Time=0.00029766909 s`, but then failed the promotion gate: 1,293 temperature
bound events, unbounded pre-correction temperatures around `306-521 K`, and
`deltaT=3.88652e-8 s` (more than 100x below its maximum). The isolated Docker
container was stopped; its log SHA-256 is
`2F278703E1D7D88387562F4792A03B6DA240F70E42331B5A9F8D56A02ADC1D0A`.

Final decision: minimal benchmark **PASS**, full-geometry calculation remains
**HOLD / FAILED_NUMERICS**. No full calculation is currently running.
The adopted instrumented solver binary SHA-256 is
`4E9CADC6CA55C0BD9287ED21571FD67B1D4E412DC2E422052288296B519A59F7`.

## Root-cause decision after R5 localization

### Evidence

- The first temperature-bound event occurs on the first solved step at
  `1.200192e-7 s` (`502.89297-503.15447 K`), while max Courant is only
  `1.3280068e-5`. The disturbance therefore precedes Courant collapse.
- The full case starts with internal `U=(0,0,0)` while the gate instantaneously
  imposes `U=(0.05,0,0)`. The passing minimal benchmark instead starts with a
  flux-consistent uniform `U=(0.05,0,0)` and uses slip/adiabatic walls.
- As R5 evolves, sampled `|U|` reaches about `483.5 m/s` in air-side cells far
  from the gate, `p_rgh` reaches about `272 kPa`, and the timestep collapses.
  Mesh quality remains acceptable (max non-orthogonality `52.40`, max skewness
  `0.622`), so mesh invalidity is not the initiating cause.
- Tight PBiCGStab temperature solves reached residuals near `1e-13` but did not
  remove the excursion. Linear solver tolerance is therefore not the root
  cause.
- Removing the standalone relaxed Tait-density overwrite did not remove the
  small-case excursion. It is architecturally unsafe but not sufficient to
  explain the R5 instability by itself.
- The custom temperature equation omits the standard compressibleInterFoam
  pressure-work and kinetic-energy coupling, while Cross-WLF is calculated only
  as `etaCrossWLF` output and is not conservatively coupled into momentum. The
  current combined model is therefore not an energy-conservative production
  formulation.

### Causal conclusion

Primary trigger (high confidence): an impulsive, flux-inconsistent startup of a
high-density-ratio compressible two-phase cavity produces an artificial pressure
wave and air-side velocity spike. Secondary amplifier (high confidence): the
screening temperature equation is not a complete conservative compressible
energy model, so the pressure/velocity transient appears as repeated temperature
bound events. Contributing model debt (medium confidence): Tait and Cross-WLF
fields are not coupled through one consistent pressure-momentum-energy closure.
Mesh quality and linear solver choice are rejected as primary causes.

### Adopted repair sequence

1. **Hydraulic startup gate:** run the full SI mesh isothermally with constant
   validated properties, an inlet velocity/alpha ramp, flux-consistent initial
   U/p fields (prepare with a potential-flow initialization where applicable),
   and no hard temperature clamp. Require max air velocity, p range, mass
   balance, and timestep stability before adding thermal physics.
2. **Thermal gate:** restore conduction with the official
   compressibleInterFoam energy terms or an explicitly derived enthalpy equation;
   log energy balance and fail on any bound event instead of accepting clipping.
3. **Rheology/EOS gate:** couple Cross-WLF viscosity into momentum and Tait
   density through the same conservative pressure correction. Validate each
   independently against analytical/material-card data before combining them.
4. **Full-cavity promotion:** require two clean repetitions, then start a new
   generation from time zero. Never resume R1-R5 checkpoints.

This ordering changes one physics layer at a time and prevents case-level
timestep tuning from masking a solver-closure defect.
