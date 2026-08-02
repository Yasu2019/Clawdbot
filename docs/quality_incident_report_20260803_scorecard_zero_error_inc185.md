# INC-185: Exact-match relative error classified as failure

## Summary

- Date: 2026-08-03 JST
- Detection: inline promotion-gate unit test failed when MF and OF pressure were identical.
- Impact: exact KPI matches can be marked failed. The measured r33 pressure gap is nonzero and remains correctly `PROXY_GAP`; no false promotion occurred.
- External web search: not used. Root cause is fully determined by local Python boolean semantics, so web evidence would not change the countermeasure.

## Observed facts

`mf_of_compare_scorecard.py` uses expressions equivalent to `abs(_rel(...) or 99)`. `_rel` correctly returns `0.0` for an exact match, but Python treats `0.0` as false and substitutes `99`.

## 5 Whys

1. Why did the exact-match test fail? Relative error zero became 99.
2. Why did zero become 99? The fallback used boolean `or` rather than an explicit `None` check.
3. Why was boolean fallback used? Missing-value and numeric-zero handling were combined in one compact expression.
4. Why was it not caught earlier? Tests covered ordinary nonzero gaps, not boundary values at exactly zero.
5. Why is this safety relevant? Promotion decisions depend on error boundaries; incorrect boundary semantics can block valid calibration or encourage manual overrides.

## FTA / Fishbone / FMEA

- Top event: wrong promotion verdict.
- Code branch: valid `0.0` enters missing-value fallback.
- Test branch: no exact-match and exact-tolerance boundary matrix.
- Process branch: scorecard previously allowed fill-only override; mandatory-KPI gate is being corrected concurrently.

| Failure mode | Effect | Severity | Detection | Countermeasure |
|---|---|---:|---:|---|
| zero error replaced by sentinel | false fail | 6 | exact-match unit test | explicit `is None` handling |
| pressure fail overwritten by fill | false pass | 10 | mixed pass/fail test | all mandatory rows must pass |
| tolerance boundary rounding | unstable verdict | 7 | boundary matrix | test below/at/above tolerance |

## Countermeasure plan

1. Replace `value or 99` with explicit `None` handling for fill and pressure relative errors.
2. Add exact match, exactly-at-tolerance, just-over-tolerance, and missing-value tests.
3. Re-run the real r33 scorecard and verify pressure remains failed at 41.46% against the 10% gate.
4. Keep `PROXY_GAP` until every mandatory KPI passes.

## Decision rule

IF a numeric KPI error is `0.0`, THEN preserve it as a valid exact match; use a missing sentinel only when the value is `None`, BECAUSE numeric zero is not missing data.

## Verification / rollback / scope

- Pass: exact match passes, 10% boundary passes, value above 10% fails, missing pressure remains `PROXY_GAP`.
- Rollback: revert only the scorecard comparison expressions and tests.
- Scope: this corrects verdict semantics; it does not improve physical solver accuracy by itself.

## Provenance

- `scripts/mf_of_compare_scorecard.py`
- `data/workspace/moldflow_bridge/mf_minusx_copy_results_20260801/inc183_r33_scorecard.json`
- INC-185, 2026-08-03 JST
