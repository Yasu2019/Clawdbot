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
