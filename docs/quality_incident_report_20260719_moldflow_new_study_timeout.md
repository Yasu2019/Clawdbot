# Moldflow MCP new-study timeout RCA (2026-07-19)

## Goal

Create an analysis-ready Moldflow 2010 study from the externally repaired STL, then place a gate and start analysis without modifying the user's source studies.

## Context and observed facts

- Host: `DESKTOP-UOVCG4T` (`100.98.133.40`), Moldflow Insight/Synergy 2010, 64-bit COM.
- MCP: bridge 0.5.4, server 1.28.1, write operations enabled.
- Source studies were preserved. `moldflow_analysis_repair_v5_auto.sdy` was created from `v4`.
- A 5 mm remesh finished `Failed`; diagnostics were unchanged before the next AutoFix.
- Second AutoFix removed 40 elements, but the result remained `Failed`: intersections 1021, overlaps 507, unoriented 101.
- `moldflow_new_study` using `Moldflow_meshfix_candidate.stl` timed out after 300 seconds.
- Expected artifact `G:\moldflow_bridge\work\CLAW_MF_AUTOREPAIR_20260719\moldflow_analysis_auto_01.sdy` did not exist.
- Read-only reinspection showed active study `moldflow_study_3.sdy`, `Midplane`, `New`, zero nodes and triangles.
- Gate placement and analysis start were not executed.

## 5 Whys

1. Why was analysis not started? The newly built study did not reach a saved, mesh-complete state.
2. Why? The MCP call timed out during the combined create/import/mesh/save operation.
3. Why was no recoverable study produced? Save occurred only after the blocking mesh call.
4. Why could the workflow not resume safely? Project creation, import, mesh launch, and save were coupled in one VBScript call with no durable checkpoint.
5. Why was this design used? The original proof-of-concept optimized for one-call execution, not Moldflow 2010's long-running, single-instance COM behavior.

## FTA / Fishbone summary

- Method: four state-changing stages coupled into one synchronous call.
- Machine: Dynabook i5-5200U; previous mesh required about 59 minutes wall time.
- API/runtime: legacy OLE automation; no proven per-instance targeting in Moldflow 2010.
- Input: welded/watertight STL passed external topology checks, but successful Moldflow import/mesh was not proven.
- Measurement: the old tool checked only after `MeshNow` returned and therefore had no durable mid-stage evidence.

## Countermeasures and decision rules

1. Split automation into `create project/study -> save -> import STL -> save -> launch mesh -> poll -> inspect quality`.
2. Never make `MeshNow` and first `Save` part of the same bounded call.
3. IF the active study identity differs from the expected scratch name, THEN stop all writes.
4. IF MeshStatus is not `Completed`, or intersections/overlaps/unoriented exceed the declared gate, THEN do not place a gate or start analysis.
5. IF a repair attempt worsens any critical metric, THEN preserve evidence and switch method; do not repeat indefinitely.
6. Gate placement must use an explicit verified surface node and be re-read after save.
7. Analysis may start only after study path existence, material assignment, mesh PASS, and gate reinspection all pass.

## Verification criteria

- A scratch `.sdy` exists before mesh launch.
- Active study canonical name matches the scratch study at every write stage.
- MeshStatus becomes `Completed`; diagnostics meet the declared safe thresholds.
- Exactly one gate is present at the selected node after save/reopen.
- `runstudy.exe` starts for the verified scratch `.sdy`; status/log shows progression or a bounded explicit failure.

## Recovery / rollback

- Reopen `moldflow_analysis_repair_v4.sdy` or the original study; neither was modified by the failed new-study attempt.
- Discard only the incomplete scratch project after verifying its exact path.
- Keep `moldflow_analysis_repair_v5_auto.sdy` as failure evidence; do not use it for analysis.

## Scope limits and next experiment

- External watertight status does not yet prove Moldflow mesh suitability.
- Material identity and process conditions are not yet verified.
- Next experiment: deploy a checkpointed MCP tool set and validate create+save only on a uniquely named scratch study before importing or meshing.

## Web knowledge check

- Autodesk documents the Synergy API as OLE automation runnable through VBScript/macros.
- Autodesk documents explicit multiple-instance API support as a feature added in the 2016 release; therefore it must not be assumed for 2010.
- These findings support single-instance, identity-checked, checkpointed execution. They do not provide a Moldflow 2010-specific recovery API.

## Provenance

- Date: 2026-07-19 JST
- Canonical prior record: `docs/knowledge/dynabook_moldflow_mcp_mesh_autofix_20260719.md`
- MCP observations captured live from `100.98.133.40:8765/mcp`.
- Autodesk references: Synergy API overview (2016 help) and multiple-instance support (2019 help describing the 2016 addition).
