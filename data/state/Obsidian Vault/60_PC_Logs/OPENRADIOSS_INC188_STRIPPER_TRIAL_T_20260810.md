# INC-188 OpenRadioss stripper hold / Trial T

## Goal and confirmed result

Isolate the stripper boundary in the four-part punch/stripper/material/die model.
Only stripper motion changed; material, GENE1 and mesh stayed fixed. Trial T
completed numerically but failed physics: ERR=-84.7%, 1,946/2,000 ruptures.

| Item | Value |
|---|---:|
| Sheet label / geometry | AA1060, temper unproven, 4 x 4 x 0.5 mm |
| Mesh | 2,000 BRICK, 20 x 20 x 5 |
| Initial gap / old / T | 0.100 / 0.190 / 0.099 mm hold |
| Punch | 2.000 mm, SPM80 crank law |
| Starter | 0 errors, 0 warnings |
| TSTOP / runtime | 3.7902 ms / 1,508.54 s |
| DT / DM/M / ERR | 7.7145 ns / 0 / -84.7% |
| Rupture | 1,946/2,000 = 97.3%; first 2.2640 ms |
| Verdict | FAILED_PHYSICAL_GLOBAL_RUPTURE |

## 5 Why, FTA and Fishbone

1. S compressed the blank because stripper travel continued after gap closure.
2. Motion was scaled from punch travel instead of held at closure.
3. No guard compared the 0.190 mm target with the 0.100 mm gap.
4. Correcting it did not solve rupture because T still ruptured 97.3%.
5. The AA1060 card and GENE1 have no traceable temper/coupon calibration.

FTA top event `false shear success` = normal TSTOP AND permissive physics gate.
Branches: boundary overtravel, uncalibrated material/deletion, and absent
force-stroke reference. Fishbone categories: model, material, boundary,
measurement and promotion logic. Trial T isolates the boundary branch.

## FMEA and QC control plan

| Failure mode | Effect | S/O/D | RPN | Control |
|---|---|---:|---:|---|
| target >= gap | bulk compression | 9/4/3 | 108 | reject before deck write |
| global deletion | false cut image | 10/7/2 | 140 | rupture <=50% gate |
| untraceable card | wrong force/fracture | 10/8/6 | 480 | temper + coupon data |
| TSTOP-only pass | bad PINN data | 10/6/2 | 120 | energy/mass/locality gates |

QC order: geometry/gap -> motion plateau -> Starter clean -> DM/M <=5% ->
energy -> localized separation -> force-stroke reference -> reproducibility ->
PINN eligibility.

## Countermeasure, rollback, next experiment

Reject stripper targets at/above 0.100 mm and verify the configured target.
Rollback: `backup/inc188-before-stripper-hold-20260810`; do not roll back the
safety gate to run 0.190 mm. Next requires exact AA1060 temper and measured
tensile/fracture or blanking force-stroke data. Public 1060-H18 values are only
screening evidence, not calibration.

Evidence: `data/workspace/openradioss_inc188_trials/INC188T_engine.log`, INC-188
RCA, local `inc188_web_knowledge` (UTF-8 replacement count 0), Beads tq1/vkc3.

Graphify root-wide update was bounded and stopped at 180 s after an unrelated
access-denied pytest directory warning. No process remained and the existing
graph was preserved. Retry only with a scoped INC-188 corpus.
