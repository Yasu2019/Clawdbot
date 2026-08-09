# INC-188 Web knowledge and Trial R/S

## Goal and physical scope

Stabilize four-part punch/stripper/material/die blanking without artificial mass,
then produce physically bounded data suitable for a future PINN surrogate.

## Web acquisition control

Four Altair official pages were verified as `direct_free`; the ASME paper
"Prediction of Ductile Fracture in Metal Blanking" was metadata-only and marked
`paid_or_subscription`. No paywall or access control was bypassed. DB table:
`inc188_web_knowledge`. UTF-8 strict decode, round-trip, mojibake marker and U+FFFD
checks all passed.

## 5 Why / FTA

Top event: full blank ruptures instead of a localized cut.

1. 1,960 of 2,000 material bricks ruptured.
2. Effective and shear thresholds were reached over almost the full blank.
3. GENE1 applies abrupt criteria rather than calibrated accumulated ductile damage.
4. Thresholds 0.35/0.30 were numerical hypotheses, not AA1060 coupon calibration.
5. No traceable AA1060 fracture constants or measured force/travel curve was present.

The previous mesh explosion was separately corrected: structured bricks increased
natural DT from 2.7439 ns to 7.7145 ns and kept DM/M=0.

## Trial evidence

| Trial | Material mesh | Result | Verdict |
|---|---|---|---|
| R | 8,000 BRICK, 0.1 mm | prefix 33.8 s; ERR=-0.0%; DM/M=0 | stable accuracy baseline |
| S | 2,000 BRICK, 0.2x0.2x0.1 mm | TSTOP 3.7902 ms; 1,553.9 s; ERR=-84.3%; rupture 98% | FAILED_PHYSICAL_GLOBAL_RUPTURE |

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Global rupture | Invalid cut | 10 | 8 | 5 | 400 | rupture fraction gate |
| Invented damage constants | False validation/PINN data | 10 | 7 | 9 | 630 | require AA1060 calibration |
| Fine tetra minimum edge | excessive runtime | 6 | 9 | 3 | 162 | structured BRICK blank |
| Encoding corruption | unusable knowledge | 7 | 5 | 7 | 245 | strict UTF-8 + DB U+FFFD check |

## QC and next experiment

- Starter 0 errors/warnings and no initial penetration.
- DM/M <=5%, no energy kill/USER BREAK.
- Rupture fraction <=50% and localized to the cutting perimeter.
- Compare force-travel and fractured surface to measurement/reference.
- Use `/FAIL/JOHNSON` or TAB1 only after AA1060 parameters are traceable.
- Never ingest Trial S as PINN training success.

Rollback: `backup/inc188-before-web-damage-20260810`.

