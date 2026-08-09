# INC-188 OpenRadioss shear Trial L-Q

## Confirmed facts

- All four solids were calculated: punch, stripper, material and die.
- Z gaps: punch-material 0.7 mm, stripper-material 0.1 mm,
  material-die 0.1 mm. The solids did not initially overlap.
- Coincident SH3N skins 101-104 duplicated the solid boundaries and generated
  artificial contact thickness/stiffness.
- Replacing skins with `/SURF/PART/EXT` produced Trial M Starter with 0 errors,
  0 warnings and no initial penetration. Short Engine: ERR about 0%,
  DM/M=3.1096%.
- Smooth SPM800 displacement reached the material. Continuous NODA/CST became
  unbounded after rupture even with a two-condition GENE1 gate.
- Trial Q natural `/DT/NODA/0`: ERR=0%, DM/M=0, DT=2.7439 ns through 0.173 ms;
  projected remaining time about 8656 s. The owned job was stopped as stable but
  performance-NG; unrelated jobs and the container remained intact.

## FTA / 5 Why

Top event: mesh explosion after cutting begins.

1. Element deletion changes the local stable time step.
2. Constant nodal control adds mass to preserve the requested step.
3. Required mass grows without a physical cap.
4. Added inertia drives further contact/deletion and energy error.
5. Exit code 0 plus `NORMAL TERMINATION USER BREAK` hid the energy-limit kill.

## FMEA and countermeasures

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Duplicate skins | False penetration/stiffness | 9 | 7 | 7 | 441 | External solid surfaces |
| Continuous CST after rupture | Mass runaway | 10 | 7 | 7 | 490 | DM/M <=5%; natural reference |
| Exit-0 energy kill | False success | 10 | 6 | 9 | 540 | Parse message 205/USER BREAK |
| Natural step too small | Excessive runtime | 6 | 9 | 2 | 108 | Bounded/local acceleration |

## QC control plan

- Starter: 0 errors, 0 warnings, 0 initial penetrations.
- Engine: no message 205/USER BREAK, ERR bounded, DM/M <=5%.
- Geometry: failure localized at cutting edge and explicit slug separation.
- Data: failed or uncalibrated trials are excluded from PINN training.

## Next experiment and rollback

Use a bounded/local time-step or staged restart and accumulated ductile damage
calibrated to 1060 material evidence. Compare against Trial Q natural stepping.
Rollback is the pushed backup branch `backup/inc188-before-geometry-20260810`.

