# Quality Incident Report: FEM Impact Mesh Explosion False SUCCESS

Date: 2026-06-24 JST

## Summary

The ThinkPad `fem_impact` track was reported as `SUCCESS` although the rendered PNGs show a severe mesh explosion. The K10 tri-track orchestrator was stopped immediately after confirmation to prevent repeated false-success loops.

## Confirmed Facts

- User reported that the FEM Impact images show mesh explosion.
- K10 log entries repeatedly marked `fem_impact` as `SUCCESS`.
- Recent `fem_impact` jobs used `FEM_IMPACT_SKIP_RECOMPUTE=png_exists` and only checked that at least 3 PNGs existed.
- Visual inspection confirmed mesh explosion:
  - `rough_displacement.png`: coordinate axes and displacement scale at approximately `1e7`.
  - `rough_peeq.png`: broken outer shape, coordinate scale at approximately `1e7`.
  - `rough_vonmises.png`: broken outer shape with only a small central stress region.
  - `sample_displacement.png`: severe exploded geometry with displacement colorbar up to approximately `8.8e+08`.
- VTK numeric ranges confirm nonphysical geometry:
  - `Rough_Mesh/test.in_surface_0.002000.vtk`: bbox diagonal approximately `5.24e7`.
  - `no_solid_reqtangle_sample_20250806/test.in_surface_0.014600.vtk`: bbox diagonal approximately `1.67e9`.
- K10 tri-track CAE orchestrator processes were stopped:
  - stopped PIDs: `28148`, `21844`.
- ThinkPad worker remains online. No Docker, container, or satellite worker service was stopped.

## Impact

- `fem_impact` results after this condition are not valid evidence of CAE success.
- Telegram / Google Drive videos generated from these PNGs may be misleading and should be treated as invalid.
- Main LAVIE and Red LAVIE CAE should not be resumed through the same tri-track orchestrator until the FEM Impact gate is fixed or FEM Impact is disabled in that orchestrator.

## 5 Whys

1. Why was a bad FEM Impact result marked `SUCCESS`?
   - The success condition accepted existing PNG count and command exit status.
2. Why was image quality not checked?
   - The gate checked `PNG_N >= 3`, not geometry plausibility or visual stability.
3. Why did the loop keep repeating the same bad result?
   - `reuse_vtk_for_png` allowed `FEM_IMPACT_SKIP_RECOMPUTE=png_exists`, so stale bad images were reused.
4. Why did prior T038 knowledge not prevent this?
   - The loop included PNG script sync and VTK glob fixes, but did not add a numeric/visual explosion gate.
5. Why did the operator miss it this session?
   - I verified logs and artifact counts, but did not open the rendered image before reporting success.

## Fault Tree

Top event: `FEM Impact false SUCCESS`

- Gate weakness
  - PNG count treated as success
  - No bbox/coordinate scale limit
  - No displacement magnitude limit
  - No stale PNG invalidation
- Solver or model instability
  - Existing VTK geometry already exploded
  - Production variants include cases with invalid deformation output
- Operational miss
  - No mandatory visual inspection before status report
  - Tri-track continuous loop repeated the bad artifact

## FMEA

| Failure mode | Effect | Severity | Occurrence | Detection | RPN | Current control | Required countermeasure |
|---|---|---:|---:|---:|---:|---|---|
| Mesh explosion rendered as success | False CAE evidence | 9 | 7 | 8 | 504 | PNG count only | Add numeric geometry gate and mark `FAILED_MESH_EXPLOSION` |
| Stale exploded PNG reused | Repeated false success | 8 | 8 | 8 | 512 | `skip_if_png_count` | Invalidate stale PNG unless QC JSON passes |
| Image not inspected before reporting | User receives misleading status | 8 | 5 | 7 | 280 | Manual ad hoc check | Require visual or numeric image QC before success report |

## Web Knowledge Check

No external web search was run for this first containment step. The root cause is local and already evidenced by local logs, PNGs, and VTK coordinate ranges. External research may be useful later for robust mesh quality metrics, but it is not needed to justify immediate containment.

## Immediate Containment

- Stop the K10 tri-track orchestrator.
- Do not resume `fem_impact` continuous mode until a gate exists.
- Treat current ThinkPad FEM Impact PNG/video artifacts from 2026-06-24 as invalid unless revalidated.

## Implemented Countermeasures

1. Added `scripts/impact_vtk_quality_gate.py`:
   - Parses legacy ASCII VTK `POINTS`.
   - Computes bbox diagonal and coordinate absolute maximum.
   - Parses displacement magnitude when available.
   - Emits `FAILED_MESH_EXPLOSION` with numeric evidence.
2. Updated `scripts/k10_tri_track_cae_orchestrator.py`:
   - Cached PNG path now runs QC before accepting `FEM_IMPACT_SKIP_RECOMPUTE=png_exists`.
   - Reused VTK path now runs QC before PNG rendering.
   - Fresh solve path now runs QC before PNG rendering.
   - Success requires `FEM_IMPACT_QC_VERDICT=PASS`.
3. Updated `scripts/k10_thinkpad_fem_impact_deploy.py`:
   - Syncs `impact_vtk_quality_gate.py` to ThinkPad with the PNG/render helpers.
4. Added persistent records:
   - `docs/INCIDENT_LOG.md` INC-129.
   - `data/state/Obsidian Vault/60_PC_Logs/FEM_Impact_INC129_mesh_explosion_false_success_20260624.md`.

## Verification After Fix

- Python compile check passed for changed scripts.
- Synthetic exploded VTK failed with `FAILED_MESH_EXPLOSION`.
- Synthetic small VTK passed.
- ThinkPad `Rough_Mesh/test.in_surface_0.002000.vtk` failed with:
  - bbox diagonal: `52376491.474604234`
  - coordinate absolute max: `26836835.687484697`
  - displacement absolute max: `26993307.7709796`
- ThinkPad `no_solid_reqtangle_sample_20250806/test.in_surface_0.014600.vtk` failed with:
  - bbox diagonal: `1668049955.5859363`
  - coordinate absolute max: `807003989.1101981`
  - displacement absolute max: `863948636.9433417`
- Live `run_thinkpad_impact` returned `FAILED_MESH_EXPLOSION`, proving stale PNG success is blocked.
