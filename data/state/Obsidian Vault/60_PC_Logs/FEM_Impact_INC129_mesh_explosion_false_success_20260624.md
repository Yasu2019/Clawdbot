# FEM Impact INC-129 Mesh Explosion False SUCCESS

Date: 2026-06-24 JST
System: K10 tri-track CAE, ThinkPad Fem_Impact
Severity: High

## Event

The user visually checked Fem_Impact PNG output and reported that the mesh had exploded. K10 tri-track had repeatedly accepted the run as SUCCESS because cached PNGs existed and the worker stdout included `FEM_IMPACT_SKIP_RECOMPUTE=png_exists` plus `FEM_IMPACT_PNG_COUNT=3`.

## Impact

- `Rough_Mesh/test.in` and `no_solid_reqtangle_sample_20250806/test.in` Fem_Impact results from this state are invalid CAE evidence.
- The tri-track loop could have kept reporting bad ThinkPad Fem_Impact artifacts while Main LAVIE and Red LAVIE appeared to be progressing normally.
- Operator trust was damaged because image reality contradicted the log verdict.

## Confirmed Measurements

| Case | VTK | bbox_diag | coord_abs_max | displacement_abs_max | Verdict |
|---|---|---:|---:|---:|---|
| Rough_Mesh | `test.in_surface_0.002000.vtk` | 52376491.47 | 26836835.69 | 26993307.77 | FAILED_MESH_EXPLOSION |
| sample | `test.in_surface_0.014600.vtk` | 1668049955.59 | 807003989.11 | 863948636.94 | FAILED_MESH_EXPLOSION |

## 5Why

1. Why was a bad image marked SUCCESS?
   - The orchestrator accepted stdout markers and PNG existence.
2. Why did PNG existence pass?
   - `skip_if_png_count` and `reuse_vtk_for_png` were designed as speed optimizations after INC-122/123.
3. Why was the source VTK not validated?
   - The prior fixes focused on deployment, globbing, and shell quoting, not physics plausibility.
4. Why did this escape operator review?
   - I reported from logs and artifact counts instead of opening the image.
5. Why was the loop able to repeat the same bad artifact?
   - Cached PNGs were treated as enough evidence and no sidecar QC existed.

## Fault Tree

Top event: Fem_Impact false SUCCESS

- Gate failure
  - PNG count accepted as success
  - No VTK bbox threshold
  - No coordinate absolute threshold
  - No displacement magnitude threshold
- Cache failure
  - `png_exists` skipped recompute
  - Existing bad VTK remained on ThinkPad
- Review failure
  - Log-only confirmation
  - No mandatory visual or numeric QC before status report

## Fishbone

Method:
- Cached PNG shortcut skipped physical validation.
- Success expression did not require a QC PASS token.

Machine:
- ThinkPad worker executed the shell job correctly, but the source data was already exploded.

Material/Data:
- VTK coordinates reached 1e7 to 1e9 scale, far beyond a plausible press panel geometry.

Measurement:
- Old KPI measured PNG count, not geometry plausibility.

Human:
- Visual review was not performed before the success report.

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Mesh explosion accepted | False CAE evidence | 9 | 7 | 8 | 504 | Require VTK numeric QC before SUCCESS |
| Stale PNG reuse | Repeated false SUCCESS | 8 | 8 | 8 | 512 | Run QC on latest VTK even when PNG exists |
| Missing visual review | Misleading user report | 8 | 5 | 7 | 280 | Treat image-sensitive CAE artifacts as unverified until visual or numeric QC passes |

## Control Plan

| Process step | Control item | Method | Reaction plan |
|---|---|---|---|
| Cached PNG acceptance | Source VTK bbox and displacement | `impact_vtk_quality_gate.py` | Return exit 20 and mark `FAILED_MESH_EXPLOSION` |
| Reused VTK render | Latest VTK sanity | Same QC script before render | Do not render or mark success if failed |
| Fresh solve | Post-solve latest VTK sanity | Same QC script before PNG render | Stop before PNG success path |
| Reporting | Success marker | Require `FEM_IMPACT_QC_VERDICT=PASS` | Do not report SUCCESS without PASS |

## Implemented Fix

- Added `scripts/impact_vtk_quality_gate.py`.
- Updated `scripts/k10_tri_track_cae_orchestrator.py` so cached PNG, reused VTK, and fresh solve paths all call the QC gate.
- Updated `scripts/k10_thinkpad_fem_impact_deploy.py` so the QC script is synced to ThinkPad with the render helpers.
- Stopped the bad tri-track loop before implementation and verified the known-bad VTK files now fail.

## Verification

- `python -m py_compile scripts/impact_vtk_quality_gate.py scripts/k10_tri_track_cae_orchestrator.py scripts/k10_thinkpad_fem_impact_deploy.py` passed.
- Synthetic exploded VTK failed with `FAILED_MESH_EXPLOSION`.
- Synthetic small VTK passed.
- ThinkPad known-bad Rough_Mesh and sample VTKs both failed.
- Live Fem_Impact single call returned `FAILED_MESH_EXPLOSION` before recompute, proving stale PNG success is blocked.

## Lessons

- Artifact count is not evidence of CAE validity.
- Any CAE path that uses cached images must validate the source field file.
- For image-sensitive deliverables, do not report success from logs alone.
