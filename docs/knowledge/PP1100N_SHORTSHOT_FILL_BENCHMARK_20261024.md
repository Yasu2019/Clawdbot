# Advanced-PP 1100 N thin-wall short-shot data connected to code

**Recorded:** 2026-10-24 JST
**Primary source:** Tran Minh The Uyen, Pham Son Minh, Bui Chan Thanh, *Polymers* 17(19), 2658 (2025), DOI [10.3390/polym17192658](https://doi.org/10.3390/polym17192658), [PMC full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC12526987/), CC BY 4.0.

## Data-to-code implementation

Added `src/openInjMoldDyMSimCr/validation/compare_advancedpp1100n_fill_ladder.py` and tests. It SHA-256-pins curated Table 8 partial-tooth (6 injection-pressure points) and Table 10 hook-leaf (4 points), checks experiment/simulation volume-percentage consistency against full-fill volume, and scores predicted fill volume and fill percentage only for an exact geometry/pressure row. The output also reports the article's own simulation-to-experiment baseline separately for each geometry and pooled.

Current published simulation-vs-experiment pooled scalar baseline from the 10 transcribed rows: fill-volume bias +12.935 mm?, MAE 13.170 mm?; fill-percentage bias +1.774 percentage points, MAE 1.832 points. Partial tooth: 6 points. Hook leaf: 4 points. These are values of the article's simulation compared with its measurements, not results from our solver.

## Limits

The material is Advanced-PP 1100 N, MFR 12 g/10 min. The data are two mold-specific fill ladders at discrete injection pressures. The paper's exact process/cooling boundary details and raw pressure histories are incomplete in the local curation. Injection pressure must not be relabelled as cavity pressure; no interpolation or generic PP calibration is justified. A solver comparison still requires matching the actual mold geometry and source pressure definition.

## Verification

Focused tests: 5 passed, covering source hash/schema/capacity checks, zero-error measured fixture, source simulation baseline, wrong geometry/pressure, and duplicate condition rejection. This does not execute OpenFOAM or prove spatial fill-field accuracy.
