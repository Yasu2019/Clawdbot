# Compressible resin/air VOF run — r5

## Verification

- Solver: `compressibleInterFoam` (OpenFOAM 2512)
- Case: 100 x 60 x 50 mm rounded-hole box, four vent patches
- Run: `endTime = 0.001 s`, adaptive time step, `maxCo = 0.02`, `maxAlphaCo = 0.01`
- Result: **PASS**; solver reached `End` with no fatal error.
- Last reported time: `0.000996952 s`; `alpha.polymer` remained bounded in `[0, 1]`.
- Thermal equation and pressure equation both converged during the run.

## Thermophysical coupling

The polymer phase is no longer `rhoConst`. It uses OpenFOAM's built-in
pressure/temperature-dependent `rPolynomial` EOS with coefficients selected as
a local expansion around the virtual reference state `Tref=508 K`,
`pref=101325 Pa`, `rhoRef=900 kg/m3`. Therefore density is evaluated inside
the thermo/energy and pressure coupling rather than being post-processed.
Air uses the compressible `perfectGas` model.

This is a **local Tait-equivalent screening model**, not an exact nonlinear
two-domain Tait implementation. The exact Tait coefficients and measured PVT
data are still pending; no production accuracy claim is made.

## Remaining work

1. Replace the local `rPolynomial` approximation with a custom nonlinear Tait
   EOS library if exact two-domain Tait behavior is required.
2. Add measured PVT, Cp, conductivity, and viscosity data and re-run the
   full fill/cooling/shrinkage/warpage sequence.
3. Perform mesh/time-step and mass/energy conservation checks on the full
   fill duration; this r5 run is a coupling smoke test, not a final molding
   result.
