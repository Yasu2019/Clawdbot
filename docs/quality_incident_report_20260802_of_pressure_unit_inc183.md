# INC-183: OpenFOAM pressure proxy mislabeled kPa as MPa

## Summary

- Detection: direct parsing of r32 OpenFOAM `p` fields during MF/OF comparison.
- NG record: `65.24 MPa` in the handoff; raw field was approximately 65,240 Pa,
  which is 65.24 kPa or 0.06524 MPa.
- Impact: calibration changed `power_law_k` from 0.05 to 0.015 in the wrong
  direction. No Moldflow source was affected. Future OF calibration would have
  underpredicted pressure further.
- Current comparison: MF EOF 13.784831 MPa vs r32 EOF 0.06517 MPa; pressure
  ratio 211.521. Fill timing remained close (MF 1.078 s; OF about 1.00-1.10 s).

## 5 Why

1. Pressure calibration was wrong because OF pressure was believed too high.
2. It was believed too high because `65.24` was labeled MPa.
3. The number came from Pa divided by 1,000, producing kPa.
4. The schema stored no source unit or conversion equation beside the proxy.
5. No regression test asserted `Pa / 1e6 = MPa` against a raw field value.

## FMEA

| Failure mode | Effect | S | O | D | Countermeasure |
|---|---|---:|---:|---:|---|
| Pa divided by 1e3 and called MPa | 1000x KPI error | 10 | 4 | 3 | typed conversion function/test |
| wrong pressure sign/direction | k moves away from target | 9 | 4 | 3 | raw-vs-target ratio gate |
| first-order k treated as validated | false precision | 8 | 5 | 2 | verification trial + PROXY_GAP |
| fill and pressure conflated | good fill hides bad rheology | 8 | 6 | 3 | separate KPI gates |

## Correction

- Added `mf_of_pressure_calibration.py` with explicit `pa_to_mpa()` and bounded
  fixed-velocity first-order k estimation.
- Corrected the handoff proxy to 0.06524 MPa.
- Proposed `k=10.576058` from `0.05*(13.784831/0.06517)` for one verification
  run; this is not yet a validated material law.
- Updated calibration DB through a recoverable backup and new active target 12.
- Preserved `PROXY_GAP`; direct Moldflow-equivalence remains forbidden.

## Verification and next experiment

- 12 related unit/handoff/pack tests pass.
- JSON handoff remains parseable.
- Next: rerun the identical r32 geometry, U=12, n=0.275 with only k changed.
- Pass band: fill completion retained; EOF pressure within the declared loose
  calibration band, then add thermo/Cool sequentially.

## Rollback and web decision

Rollback code/data to the prior Git commit and restore
`mf_of_calibration_pre_inc183_20260802.sqlite`. Web search was not used: the raw
private OpenFOAM field and SI conversion supplied definitive evidence.

