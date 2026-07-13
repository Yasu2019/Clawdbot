# Moldflow 2010 vs Moldflow CAE Studio — first calibrated comparison

Date: 2026-07-13

## Matched test case

- Geometry: PP plate, 100 x 60 x 2 mm
- Gate: one enabled center-gate proxy (`inlet2`) in CAE Studio
- Material: PP generic
- Melt temperature: 513 K (240 C)
- Mold temperature: 323 K (50 C)
- Analysis: Fill / resin-fill VOF
- CAE Studio trial: `moldflow_real_compare_pp_plate_20260713`
- Real Moldflow reference: `pp_plate_100x60x2_study_(copy_3)`

The CAE Studio job was exported through its port 8776 API and executed by
`cae_te_remote_trial.py`. The preflight and OpenFOAM mesh check passed.

## Results

| Metric | Moldflow 2010 | CAE Studio | Assessment |
|---|---:|---:|---|
| Fill completion | Successful | Short shot | Fail |
| Fill fraction | 100% | 69.83% | -30.17 percentage points |
| Fill time | 0.9000 s setting; flow reaches 100% near 0.977 s | 0.1361 s at failure | Not comparable; proxy terminates early |
| Maximum polymer volume fraction | physically bounded | 7.91041 | Nonphysical; must be <= 1.0 |
| Mass-balance error | not exported as same KPI | 0.12% | Proxy diagnostic only |
| Part weight | 9.0911 g | not calculated | Missing KPI |
| Maximum injection pressure | 10.8794 MPa | not calculated | Missing KPI |
| Maximum clamp force | 3.0160 tonne | proxy only estimates required 12.0 kN | Definition/unit alignment required |
| Maximum bulk temperature | 241.0592 C | not calculated | Missing KPI |
| Maximum wall shear stress | 0.1644 MPa | not calculated | Missing KPI |
| Maximum shear rate | 5565.3267 1/s | not calculated | Missing KPI |

## Verdict

CAE Studio correctly accepts the real geometry, gate specification, material
preset, and process inputs, and its mesh precheck passes. Its current
`resin_fill_cad` / VOF solver is **not yet quantitatively valid** for this
100 x 60 x 2 mm reference. The principal blocker is numerical boundedness:
`alpha.polymer` grows far above 1, after which the run is classified as
`openfoam_numerical_blowup` and `FAILED_SHORT_SHOT`.

## Improvement priority

1. Enforce bounded phase fraction (`0 <= alpha.polymer <= 1`) and fail fast on
   the first violation above 1.05.
2. Calibrate inlet boundary condition/end time to the Moldflow reference fill
   time (0.9–0.98 s), rather than accepting the current 0.1361 s partial fill.
3. Use the exact gate coordinate/node exported from Moldflow, instead of the
   coarse named-patch `inlet2` proxy.
4. Add directly comparable outputs: injection pressure, part weight, bulk
   temperature, wall shear stress, and shear rate.
5. Only after bounded complete filling is achieved, tune viscosity and thermal
   parameters against the real reference.

## Evidence paths

- Exported Studio job: `data/cae_te_workspace/jobs/moldflow_studio/moldflow_real_compare_pp_plate_20260713.json`
- Exported parameters: `data/cae_te_workspace/jobs/moldflow_studio/moldflow_real_compare_pp_plate_20260713_params.json`
- Studio run directory: `data/cae_te_workspace/runs/moldflow_real_compare_pp_plate_20260713`
- Real Moldflow analysis log on Dynabook: `G:\MoldflowRemote\workspace\results\pp_plate_fusion.log`

## P0 bounded-alpha trials (2026-07-13)

| Trial | Change | Fill | Fill time | Extracted alpha max | Decision |
|---|---|---:|---:|---:|---|
| baseline | existing settings, inlet 1.0 m/s | 69.83% | 0.1361 s | 5.3287 | reject |
| candidate 1 | bounded-alpha controls, inlet 1.0 m/s | 71.54% | 0.1395 s | 5.0340 | reject; improved but nonphysical |
| candidate 2 | candidate 1 + inlet 0.15 m/s, end 0.15 s | 8.59% | 0.1038 s | 1.0000 | diagnostic pass for early-time boundedness |
| candidate 3 | candidate 2 + end 1.1 s | 81.09% | 1.0594 s | 10.5252 | reject; late-time instability |
| candidate 4 | candidate 3 + split alpha/compression schemes | 75.18% | 0.9926 s | 11.1381 | reject; worse than candidate 3 |

Candidate 2 proves that a lower inlet velocity can keep alpha bounded during
the early fill. Candidate 3 also brings the reported fill time close to the
commercial reference, but alpha becomes unbounded later. Therefore inlet
velocity/end-time calibration is useful, while the next P0 investigation must
target the late-fill alpha boundary/transport behavior. Candidate 4's scheme
split must not be promoted.

Two earlier candidate-1 attempts are excluded from this table because the
candidate settings were not present in their generated run directories. They
are configuration-distribution failures, not physics results.

The case builder now supports `analysis_end_time_s`, allowing each benchmark
to set its analysis horizon without mutating the shared OpenFOAM template.

## P0 continuation: vent boundary and strict completion gate

| Trial | Boundary/topology | Fill | Time | Alpha max | Decision |
|---|---|---:|---:|---:|---|
| candidate 5 | velocity outlet only; alpha fixed to zero | invalid | 1.1 s horizon | 38.6018 | reject; inconsistent vent pair |
| candidate 6 | pressure vent + alpha inlet/outlet | 61.96% | 1.096174 s | 1.0000 | bounded short shot |
| candidate 6 repeat 2 | identical to candidate 6 | 61.96% | 1.096174 s | 1.0000 | reproducibility pass |
| candidate 6 repeat 3 | identical to candidate 6 | 61.96% | 1.096174 s | 1.0000 | reproducibility pass |
| candidate 7 | candidate 6, velocity 0.28 m/s | 85.47% | 1.016165 s | 1.0000 | reject as short shot under strict gate |
| candidate 8 | candidate 6, velocity 0.335 m/s | 88.56% | 0.991796 s | 1.0000 | reject as short shot |
| candidate 9 | corner vents, velocity 0.205 m/s | 81.93% | 1.001887 s | 1.0000 | reject; topology direction retained for refinement |

The former 80% completion threshold produced a false SUCCESS for candidate 7.
The benchmark completion threshold is now 98%; the continuous supervisor's
promotion hard gate remains 99%. Candidate 6 proves boundedness three times
with identical KPIs, so bounded alpha is reproducible. It does not prove full
fill and is not promoted as a complete solver configuration.

Root causes and durable rules:

1. A closed incompressible cavity with continuous prescribed inflow cannot be
   treated as a valid mold-air model. It caused late-fill alpha accumulation.
2. Opening only the velocity outlet while fixing outlet alpha to zero is an
   inconsistent boundary pair and caused worse accumulation.
3. A pressure inlet/outlet velocity plus alpha inlet/outlet pair keeps alpha in
   [0, 1], but a large far-edge vent allows polymer loss before corner fill.
4. Increasing velocity alone cannot correct that topology; vent geometry and
   gate geometry must be calibrated together.
5. OpenFOAM time-directory names must be used verbatim. Formatting a parsed
   float with `:g` changed `1.096174` to a nonexistent `1.09617`, yielding a
   false zero-fill KPI.
6. The normal OpenFOAM startup message that FPE trapping is enabled is not a
   floating-point crash and must not receive the `foam_fpe` tag.
7. Inlet-only mass balance is invalid for a vented case until outlet phase flux
   is integrated; the supervisor now reports it as skipped instead of a false
   error percentage.

Official implementation references used for the alpha-control audit:

- OpenFOAM v2512 multiphase system source reads alpha controls through the
  solver dictionary and applies MULES limiting:
  https://api.openfoam.com/2512/multiphaseInter_2phasesSystem_2multiphaseSystem_2multiphaseSystem_8C_source.html
- OpenFOAM alpha controls document `nAlphaCorr`, `nAlphaSubCycles`, and
  `MULESCorr`:
  https://api.openfoam.com/2406/src_2finiteVolume_2cfdTools_2general_2include_2alphaControls_8H.html

## P1 completion: compressible trapped-air model

| Trial | Change | Result | Fill | Time | Alpha max |
|---|---|---|---:|---:|---:|
| candidate 10 | 4 mm gate, two 2 mm vents | short shot | 57.75% | 1.038929 s | 1.0 |
| candidate 11 | vents reduced to 0.2 mm | timeout at 15 min | 42.42% at 0.680789 s | partial | 1.0 |
| candidate 12 | compressible air, closed cavity | thermal failure after fill | 100% | 0.993358 s | 1.0 |
| candidate 13 | stop before air-phase singularity | final log 98.28%; stored 97.73% | 97.73% | 0.969604 s | 1.0 |
| candidate 14 | synchronized 5 ms output | success | 98.27% | 0.975 s | 1.0 |
| candidate 15 | inlet velocity 1.510 m/s | success | 98.92% | 0.970 s | 1.0 |
| candidate 16 | inlet velocity 1.512 m/s | success | 99.05% | 0.970 s | 1.0 |
| candidate 16 repeat 2 | identical | success | 99.05% | 0.970 s | 1.0 |
| candidate 16 repeat 3 | identical | success | 99.05% | 0.970 s | 1.0 |

Candidate 16 passes the continuous-improvement hard gates three times with
zero KPI spread. Its stored fill time is 0.970 s; the final solver time is
0.976923 s, within 0.008% of the real Moldflow reference near 0.977 s. Final
temperature is also deterministic at 323.058--477.337 K. This promotes the
improvement program from P1 complete-fill work to P2 commercial KPI
calibration. It does not authorize automatic production promotion.

Durable rules from this stage:

1. Incompressible air plus a closed cavity is mathematically inconsistent for
   prescribed injection. A compressible gas phase is required when the cavity
   has no physical vent.
2. Continuing until alpha is exactly one removes the gas phase and makes the
   two-phase thermal solve singular. Stop at the validated near-complete fill
   threshold before the gas volume reaches zero.
3. Solver logs and stored fields are different evidence. Synchronize output in
   physical time (`adjustableRunTime`) before using the field as a promotion KPI.
4. A candidate is not reproducible merely because it succeeded once. Candidate
   16 required three identical hard-gate passes and the supervisor now records
   their spread explicitly.

## P2 injection-pressure calibration (candidates 17-20)

Pressure is now defined as the maximum, over synchronized written times, of
the enabled injection-gate patch face-average absolute pressure minus the
initial atmospheric pressure. This remains an OpenFOAM gate-pressure proxy,
not a claim of complete commercial equivalence.

| candidate | change | fill | fill time | gate pressure | error vs 10.8794 MPa | result |
|---|---|---:|---:|---:|---:|---|
| 17 | 0.001 s synchronized writes | 99.12% | 0.976 s | 13.712825 MPa | 26.0439% | rejects misleading coarse sampling |
| 18 | velocity 1.5085 m/s | 99.02% | 0.976 s | 12.316075 MPa | 13.2055% | fill passes, pressure fails |
| 19 | Cross-WLF D1=2.6e9, mu=293.293 Pa s | 99.02% | 0.976 s | 12.224275 MPa | 12.3617% | trapped air dominates |
| 20 | consistent p=p_rgh=101325 Pa initially | 99.02% | 0.976 s | 11.227875 MPa | 3.2031% | passes all current gates |

Candidate 20 was repeated three times. Fill, time, alpha maximum, and pressure
were identical in all three runs, so their observed spreads are zero. The
supervisor now requires the injection-pressure tolerance as well as bounded
fill for all three promotion-evidence runs. Automatic production promotion
remains disabled.

Durable pressure-calibration rules:

1. Write the final pressure field at the commercial comparison time; a coarse
   0.005 s interval missed the steep end-of-fill pressure rise.
2. With zero gravity, initialize `p_rgh` consistently with absolute `p`.
3. Pass Cross-WLF parameters into the generated OpenFOAM polymer viscosity;
   a parameter present only in trial JSON is not evidence it affected the solver.
4. Tune one pressure driver at a time and preserve fill, alpha, mesh, and
   convergence gates.

## P3 part-weight calibration (candidate 21)

The STEP and generated mesh both describe a 100 x 60 x 2 mm cavity, or
12,000 mm3. Candidate 20 still used the template's fixed polymer density of
1,200 kg/m3 and therefore predicted 14.259284 g at 99.02% fill, 56.8488%
above the commercial 9.0911 g result.

Candidate 21 introduced an explicit `polymer_density_kg_m3` material parameter
of 765.067862 kg/m3. This is an effective melt-density calibration at the fill
state, not a solid room-temperature density claim. Results were:

- fill: 99.02% at 0.976 s;
- alpha maximum: 1.0;
- maximum gate-pressure proxy: 11.224775 MPa, 3.1746% from commercial;
- part-weight proxy: 9.091128 g, 0.0003% from commercial.

Three independent Candidate 21 runs produced identical fill, time, pressure,
and weight values. The supervisor promotion evidence now requires all four KPI
families and records the part-weight spread explicitly. The next sequential KPI
is maximum bulk temperature versus 241.0592 C.

Durable weight-calibration rules:

1. Verify STEP/mesh cavity volume before treating a mass difference as a
   material-density difference.
2. Compute weight from the written alpha field, cavity volume, and the same
   density actually supplied to the solver.
3. Distinguish effective melt density at filling temperature from solid PP
   density; retain the calibration provenance.
4. Recheck pressure and fill after density changes, even when the mass formula
   itself is deterministic.

## P4 maximum bulk-temperature calibration (candidate 22)

The two retained final fields underreported the commercial maximum because the
temperature peak occurs during filling. Candidate 22 therefore added two
lightweight OpenFOAM runtime histories without retaining every full field:

- `fieldMinMax(T)` every time step;
- `weightedVolAverage(T)` using `alpha.polymer` as the weight field.

The actual history contained 5,196 samples. Results were:

- history maximum temperature: 239.85 C;
- commercial maximum bulk temperature: 241.0592 C;
- difference: -1.2092 C, or 0.5016%;
- final polymer-cell maximum alone: 204.131 C;
- peak alpha-weighted whole-cavity temperature: 219.8552 C.

The 239.85 C history maximum is used as the one-cell-thickness bulk-temperature
proxy. Candidate 22 was repeated three times; fill, time, alpha, pressure,
weight, and maximum-temperature values were identical, with zero observed
spread. The next sequential calibration is wall shear stress and shear rate.

Durable thermal-calibration rules:

1. Preserve the time history for a history-defined commercial KPI; a final
   field is not a valid substitute.
2. Store reduced scalar histories rather than thousands of full fields during
   continuous operation.
3. Record both the selected comparison proxy and alternative diagnostics so
   later mesh/thickness improvements can revise the definition transparently.
4. Apply cooldown to both automatic and manually launched reference trials to
   prevent duplicate solver runs.
