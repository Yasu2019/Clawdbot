# Box-roundhole gate/vent improvement — 2026-09-08

## Decision

The former geometry classified complete x-end faces as `gate` and `vent`.
That violated the two Ø4 mm gate requirement and produced an inlet edge
singularity. The generator now imprints two circular gate disks at
`(0,15,25)` and `(0,45,25)` mm and two screening vent disks at
`(100,15,25)` and `(100,45,25)` mm. The vent dimensions remain an explicit
tooling assumption pending the authoritative drawing; they are not promoted
as production truth.

## Evidence

- `geometry_gatevent_r4`: CAD volume `41323.68146928206 mm3`, analytic volume
  `41323.68146928204 mm3`, relative error `5.3e-16`.
- OpenFOAM `gatevent_mesh_preflight_r2`: SI bounding box
  `(0,0,0)-(0.1,0.06,0.05)`, one connected region, max non-orthogonality
  `66.54`, max skewness `0.9024`. The strict all-geometry check reports
  2,122 small-determinant tetra cells; this remains a mesh-quality follow-up,
  not a silent pass.
- Patch audit: gate area `24.7594 mm2` (equivalent diameter `3.970 mm`), vent
  area `5.94705 mm2` (equivalent diameter `1.950 mm`), centroids at the
  requested x/y/z positions. Both pass the 3% equivalent-diameter mesh
  tolerance.
- `gatevent_isothermal_acceptance_r1` and `_r2` both ended at `0.003 s`,
  bounded alpha `[0,1]`, no temperature-bound events, final max Co
  `0.012329`, and identical SHA-256 hashes for `U`, `p_rgh`, `alpha.polymer`,
  `T`, and `rho`.

## Physics status

The current screening solver has a conservative storage/advection/conduction
temperature equation, but pressure work and viscous heating remain disabled.
Cross-WLF is evaluated and written as `etaCrossWLF` but is not yet the
constitutive viscosity in `divDevRhoReff`. Tait density is evaluated in the
solver and blended into `rho`, but the phase thermodynamic `rho1/psi1` used by
the pressure equation is still the constant-property phase closure. Therefore
thermal, Cross-WLF, Tait, calibration, cooling/shrinkage/warpage, and full-fill
claims remain blocked until a commercial-grade material card and process data
are supplied and the constitutive coupling is implemented and validated.

## Required inputs before promotion

Commercial grade and authoritative Cross-WLF/pvT coefficients with units,
melt/mold temperatures, injection/packing/cooling schedule, gate pressure or
flow history, and calibrated elastic/thermal shrinkage properties.
