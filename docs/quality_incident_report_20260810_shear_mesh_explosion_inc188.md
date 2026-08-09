# INC-188: Shear blanking mesh explosion and false physical SUCCESS

Date: 2026-08-10 JST

## Summary

OpenRadioss run59 reached 20 ms and `NORMAL_TSTOP`, but its final energy error was
`-99.9%`. The stored status nevertheless had `gate_passed=true`. FEM Impact also
timed out and the tri-track was repeatedly emitting `SKIP_STORAGE`. No current
result proves stable shear separation.

## Observed facts

- OpenRadioss run59: 20.0 ms, `NORMAL_TSTOP`, energy error `-99.9%`.
- FEM Impact trial `tri-thinkpad-fem_impact-9bcc167f`: timeout, exit 124.
- Current fail streaks: OpenRadioss 10; FEM Impact 20.
- The regression fixture named an `ERR=-98.4%`, `DM/M=8.8558%` run healthy.
- DB backfill classified `NORMAL_TSTOP` as success without an energy gate.
- Prior failure evidence recorded contact-node relative velocity near 3591 m/s.

## 5 Why

1. Mesh-exploded results were accepted because termination time was the main gate.
2. Extreme post-fracture energy loss was explicitly excluded from success logic.
3. The regression fixture encoded that exclusion as expected healthy behavior.
4. DB ingestion repeated the same termination-only rule.
5. Contact deletion, added mass, energy balance, geometry and cut completion were
   not required together as one promotion contract.

## FTA

Top event: false successful shear analysis.

- Numerical divergence: excessive contact penetration; deleted nodes remain in
  contact; excessive erosion; time-step or mass-scaling intervention.
- Gate defect: `NORMAL_TSTOP` accepted; extreme final energy loss ignored;
  geometry/separation evidence optional.
- Data defect: stale or invalid success was propagated to status and DB.

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Extreme energy loss accepted | False CAE success | 10 | 7 | 8 | 560 | Fail at final ERR <= -95% |
| Added mass above guidance | Distorted inertia | 9 | 6 | 7 | 378 | Require DM/M <= 5% |
| Deleted node re-contact | Mesh explosion | 10 | 6 | 7 | 420 | Audit TYPE7/25 deletion handling |
| Termination-only DB record | Invalid training data | 9 | 7 | 8 | 504 | Apply physical gate before ingest |

## Web evidence

- Altair TYPE7 FAQ: deleted-element nodes must be removed from contact with
  `Idel=1/2`; initial penetration and unrealistic gap/contact stiffness can
  collapse the time step.
- Altair Results Checking: energy error approaching +/-99% can indicate divergence.
- Altair Nodal Time Step Control: added mass should generally remain below 5%.
- Altair time-step limitations: constant time-step controls cannot repair bad
  TYPE7 behavior and may create near-infinite added mass.

## Decision rule

IF a blanking run reaches TSTOP but final energy error is <= -95%, added mass is
>5%, geometry QC fails, or cut-completion evidence is absent, THEN record FAILED
and exclude it from PINN training BECAUSE termination alone does not prove a
bounded physical solution.

## Correction and verification plan

1. Invalidate run59 physical success.
2. Tighten energy and mass gates and regression tests.
3. Audit contact deletion/gap and failure model on a bounded coupon.
4. Require stable geometry, energy, mass, velocity and separation KPIs together.
5. Only then run production geometry and generate PINN surrogate training data.

## Scope limits

This incident correction does not yet validate a material failure calibration,
commercial-equivalent shear surface, burr height or 0.1-second PINN inference.

## 2026-08-10 trial evidence (A-K)

- Root deck defect: TYPE25 values were whitespace-packed instead of placed in
  the documented 10-column fields. Radioss therefore read `Inacti=0` and
  incomplete cards. `/PROP/SOLID` also omitted the mandatory title/third card.
- Solver mismatch: every solid element is `/TETRA4`, while both properties used
  HA8 `Isolid=14`. Trial G changed only these properties to tetra-compatible
  `Isolid=1`; element/property warnings fell from 60 to 2.
- Trial H Starter: 0 errors, 6 warnings (2 shell auto-integration and 4 initial
  penetration warnings), versus 66 warnings before mesh/formulation repair.
- Trial H Engine failed the mass gate immediately: `DM/M=31.089%` at `DT=1e-7 s`.
- Trial I at `DT=1e-8 s`: `DM/M=0.0891%`; bounded through `3.4e-5 s`, but stopped
  at the predeclared 120 s calibration limit.
- Trial J at `DT=4e-8 s`, `TSTOP=3e-5 s`: NORMAL TERMINATION in 34.05 s,
  751 cycles, final `ERR=-14.9%`, `DM/M=4.1804%`. This is a stable calibration
  completion, not proof of shearing/separation.
- Full-duration trial K retained `DM/M=4.1806%` but energy error deteriorated to
  `-32.8%` by `1.64e-4 s`; it was stopped as a failed physical trend. No solver
  process was intentionally left running.

Revised rule: a short stable prefix can promote a time-step setting to a longer
experiment, but cannot promote the analysis or PINN dataset. Full-duration
energy, bounded geometry and actual slug separation remain mandatory.
