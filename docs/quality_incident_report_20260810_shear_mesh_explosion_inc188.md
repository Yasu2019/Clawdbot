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

## 2026-08-10 geometry/contact and time-step evidence (L-Q)

- The four physical solids were explicitly audited: punch Z=1.2..2.9 mm,
  material Z=0..0.5 mm, die Z=-0.6..-0.1 mm and stripper Z=0.6..1.1 mm.
  The solid gaps are therefore 0.7, 0.1 and 0.1 mm; the reported initial
  penetrations were not solid-body intersections.
- Parts 101-104 were coincident SH3N skins duplicating every solid boundary.
  Replacing them with `/SURF/PART/EXT` surfaces removed artificial shell
  stiffness/contact thickness. Trial M Starter then had 0 errors, 0 warnings
  and no initial penetration; its 3e-5 s Engine prefix ended normally with
  ERR about 0% and DM/M=3.1096%.
- The original punch speed and TSTOP moved the punch only about 0.055 mm after
  its 0.7 mm approach gap, so historical runs never reached the sheet.
- Smooth SPM800 displacement reached contact, but trials O/P using continuous
  `/DT/NODA/CST` suffered rupture cascades, ERR=99.9% and effectively unbounded
  DM/M. Adding a two-condition GENE1 effective/shear gate delayed but did not
  remove the instability.
- Trial Q used `/DT/NODA/0` (natural step): through T=1.73e-4 s it maintained
  ERR=0.0% and DM/M=0 with DT=2.7439e-9 s. The projected remaining time was
  about 8656 s, so the owned trial was deliberately stopped as stable but too
  slow. No unrelated solver process was stopped.
- The result gate now treats `RUN KILLED: ENERGY ERROR LIMIT REACHED` and
  `NORMAL TERMINATION USER BREAK` as failures even when the process exits 0.

Revised next experiment: use a bounded/local time-step control or staged restart
that enforces DM/M <=5%, and calibrate accumulated ductile damage before claiming
cut completion. Natural stepping is the reference truth run, not the fast path.

## 2026-08-10 web knowledge and structured-blank trials (R-S)

- Five bounded sources were ingested into `inc188_web_knowledge`: four official
  Altair pages and metadata for DOI 10.1115/1.1285909. The ASME full text was
  classified `paid_or_subscription` and was not downloaded. UTF-8 strict decode,
  round-trip validation, mojibake-marker rejection and U+FFFD DB checks passed.
- Official `/FAIL/JOHNSON` documentation identifies plastic-strain failure with
  linear accumulated damage. No traceable AA1060 damage constants were found;
  constants from another alloy/example must not be used as calibration.
- Mesh audit found no tetra quality below 0.1, but the material minimum edge was
  30.681 micrometers and controlled the 2.7439 ns natural step.
- Trial R replaced 48,096 material tetrahedra with 8,000 0.1 mm structured
  bricks. Starter: 0 errors/warnings. Natural prefix: DT=7.7145 ns, ERR=-0.0%,
  DM/M=0, 3,890 cycles and 33.8 s.
- Trial S used 2,000 bricks (0.2 mm in-plane, 0.1 mm through thickness).
  It completed TSTOP=3.7902 ms in 1,553.9 s with no mass scaling or energy kill.
  However ERR=-84.3% and 1,960/2,000 elements ruptured across nearly the full
  material bbox. Verdict: FAILED_PHYSICAL_GLOBAL_RUPTURE, screening only.
- The gate now counts unique `RUPTURE OF SOLID ELEMENT` IDs and fails a configured
  material rupture fraction above 50%. Trial S is excluded from PINN training.

Decision: structured bricks solve the dominant time-step cost and stop the mesh/
mass explosion, but GENE1 remains physically uncalibrated. The next solver trial
is blocked on defensible AA1060 accumulated-damage calibration or measured blanking
force/fracture data; numerical threshold guessing would create false training data.
