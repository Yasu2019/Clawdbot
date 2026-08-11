# Global Result Truth Gate

## Purpose

Prevent an AI-generated or software-generated artifact from being reported as a
correct engineering result merely because execution finished or the output looks
plausible. This specification applies to every Clawstack application and every
future app.

## Status model

| Status | Meaning | User-facing conclusion allowed |
|---|---|---|
| `EXECUTED` | Program produced an artifact | No |
| `UNVALIDATED` | Some evidence exists, required gates incomplete | No |
| `HOLD` | Contradiction, stale evidence, or unresolved uncertainty | No |
| `FAILED_PHYSICS` | Domain bounds or conservation failed | No |
| `FAILED_NUMERICS` | Convergence, mesh, conditioning, or statistics failed | No |
| `INSUFFICIENT_EVIDENCE` | Claim exceeds available evidence | No |
| `VALIDATED` | All required independent gates passed for declared scope | Yes, within scope |
| `PRODUCTION_READY` | Validated plus deployment monitoring and rollback passed | Yes, within scope |

`SUCCESS` by itself is prohibited because it conflates execution success and
result validity.

## Evidence classes

Every report must label each important statement as one of:

- `FACT`: directly observed input, log, measurement, or file property.
- `CALCULATION`: reproducible transformation of stated inputs and equations.
- `ASSUMPTION`: necessary value not independently established.
- `INFERENCE`: interpretation supported by evidence but not directly observed.
- `RECOMMENDATION`: proposed action and its expected trade-off.

Assumptions and inferences must not be rewritten as facts in dashboards,
presentations, videos, or notifications.

## Universal required checks

1. Correct input identity and immutable hash.
2. Configuration, units, coordinate system, software/model version, and seed.
3. Complete execution log without timeout, parser failure, hidden fallback, or
   stale cached output.
4. Domain bounds and invariants.
5. Numerical or statistical quality.
6. Sensitivity to at least one important uncertain input.
7. Reference comparison with a declared tolerance.
8. Clean rerun or independent reproduction.
9. Uncertainty and known limitations.
10. Independent validation of the exact user-facing claim.

If a check is not applicable, the app must record a specific reason and an
alternative control. `N/A` without justification fails the gate.

## Domain minimums

| Domain | Examples of mandatory evidence |
|---|---|
| Resin molding / CFD | closed geometry, mesh quality, mass conservation, bounded phase fraction, convergence/Courant evidence, material/process provenance, commercial or measured correlation |
| CETOL / tolerance | datum and loop correctness, units, distribution assumptions, sensitivity contribution sum, Monte Carlo/analytic cross-check, drawing-based benchmark |
| DXF to 3D | scale/units, topology/manifoldness, volume/bounds, feature-count comparison, section/view comparison against source drawing |
| AI appearance inspection | specimen and label provenance, train/test separation, confusion matrix, per-defect recall, false-positive rate, threshold calibration, drift and representative holdout testing |
| OpenRadioss / FEM Impact | model checks, material/units, contacts and constraints, energy balance, timestep/mass scaling, convergence, mesh study, test or trusted-reference correlation |
| Sn/Ni plating composition | instrument calibration, blank/standard, units and detection limits, replicate dispersion, mass-balance/chemistry plausibility, certified reference or laboratory comparison |

These are minimums. App-specific standards and customer specifications remain
authoritative when stricter.

## Independence rule

The same AI/model cannot create a result and validate it by reflection or a
second prompt. Acceptable independent evidence includes a different physical
method, analytical calculation, separately implemented checker, calibrated
measurement, certified reference, locked holdout dataset, or named human/domain
review. Different model names using the same unverified input are advisory only.

## Claim wording gate

Terms such as `proved`, `complete match`, `exact`, `perfect`, `commercial
quality`, and `production ready` require `PRODUCTION_READY` evidence explicitly
supporting that wording. Otherwise use bounded wording such as `simulation
suggests`, `preliminary`, or `unvalidated estimate`, followed by the missing
evidence.

## Machine-readable contract

Run:

```text
python scripts/global_result_truth_gate.py result_evidence.json
```

Exit code 0 means the declared claim level is permitted. Exit code 2 means the
result must not be promoted or reported as validated. The validator never turns
a failed solver or missing evidence into a successful conclusion.

## Historical-output rule

Existing reports are not retroactively trusted. Recheck high-impact historical
claims, beginning with safety, tooling, process settings, customer-facing
reports, and claims using absolute wording. Until rechecked, display
`UNVALIDATED_LEGACY_RESULT`.
