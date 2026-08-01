# Moldflow vs OpenFOAM multiphysics campaign

- Study: `mf_fc_warp_v2_20260720_(copy)_minusX`
- Catalog: **468** results
- OF trials: **8**
- Label: **PROXY_GAP**

## Coverage

| State | Count |
|---|---:|
| MF_COOL_SOLVED_FIELD_EXPORT_PENDING | 28 |
| MF_UNAVAILABLE_ON_FLOW_WARP | 23 |
| PENDING_MF_EXPORT | 353 |
| PENDING_OF_EXTRACTOR | 61 |
| READY_COMPARE | 3 |

## Priority

1. **fill** - spatial RMSE for fill time/front and completion
2. **pressure_pack** - pressure history/field error; calibrate rheology and V/P switch
3. **cooling** - export solved MF Cool fields; compare freeze/cycle/T fields with queued OF Cool
4. **sink_shrink** - replace pack-ratio-only proxy with PVT/thermal shrink calibration
5. **warpage** - compare nodal displacement after calibrated pack+cool history
6. **weldline** - compare ridge coordinates and distance distribution; location only

## Cooling gate

Moldflow Cool solved successfully: cycle=35.0 s, part surface average=342.2514 K. Field plots still require CSV export before spatial comparison.
