# INC-152 Dynabook Moldflow MCP Mesh/AutoFix

## Result

MCP control achieved copy creation, mesh launch/monitoring, mesh diagnostics, AutoFix, save, and quantitative reinspection. Analysis was correctly blocked because the repaired mesh remained failed.

## QC process flow

Original protected -> SaveAs copy -> exact-name check -> mesh -> quality metrics -> AutoFix copy -> save -> remeasure -> PASS: gate/analysis; FAIL: stop and repair geometry.

## FMEA

| Failure mode | Effect | Cause | Control |
|---|---|---|---|
| MCP in another Windows session | No active study | remote/service restart | start MCP beside visible Synergy |
| Export during mesh | synmesh stalls | UDM file contention | skip ExportModel while Running/Pending |
| AutoFix accepted without recheck | invalid analysis | output-count-only judgment | full quantitative reinspection |
| Wrong mesh representation | invalid workflow | global Midplane setting | verify Fusion before mesh |

## 5 Why / FTA / fishbone

- Top event: automatic Fill analysis cannot safely start.
- Geometry: intersections 1,052; overlaps 529; unoriented 95 after AutoFix.
- Method: repeated inspection originally exported the live model during meshing.
- Machine: i5-5200U, two cores, prolonged 100% load.
- Environment: visible Synergy and remotely restarted MCP could occupy different sessions.
- Measurement: `AUTOFIX_REMOVED=174` showed execution, not mesh acceptance.

## Countermeasures

1. Copy-only writes and exact active-study checks.
2. 64-bit COM and same interactive Windows session.
3. No `ExportModel` during mesh.
4. Require post-AutoFix quality metrics before gate or analysis.
5. Re-import repaired STL into a fresh Fusion study for the next trial.

Canonical record: `docs/knowledge/dynabook_moldflow_mcp_mesh_autofix_20260719.md`.
