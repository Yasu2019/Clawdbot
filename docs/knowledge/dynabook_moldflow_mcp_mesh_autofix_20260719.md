# Dynabook Moldflow 2010 MCP Mesh/AutoFix Know-how (2026-07-19)

## Goal and context

- Goal: control Autodesk Moldflow Insight 2010 on Dynabook through MCP while preserving the original study.
- Host: `DESKTOP-UOVCG4T`, Tailscale `100.98.133.40`.
- Bridge: `G:\moldflow_bridge\moldflow_mcp_server.py`, MCP `:8765`, version 0.5.4.
- Moldflow: Synergy 2010, 64-bit COM registration.
- Safety: modify verified copies only; do not start analysis when mesh quality fails.

## Confirmed achievements

1. Tailscale and MCP connectivity were restored and verified by service identity, not merely by a listening port.
2. Synergy COM was controlled through 64-bit `cscript.exe` in the same interactive Windows session as Moldflow.
3. `StudyDoc.SaveAs` created repair copies without changing `moldflow_study_3`.
4. MCP started `MeshNow(False)` and observed `Pending -> Running`.
5. MCP inspected node/triangle counts, mesh status, intersections, overlaps, unoriented elements, and NDBC gate count.
6. `MeshEditor.AutoFix()` ran on `moldflow_analysis_repair_v4`, removed 174 elements, saved the copy, and was quantitatively rechecked.
7. The quality gate correctly prevented gate placement and analysis on a failed mesh.

## Evidence table

| Metric | Before AutoFix | After AutoFix |
|---|---:|---:|
| Nodes | 4,920 | 4,920 |
| Triangles | 9,846 | 9,801 |
| Intersections | 1,201 | 1,052 |
| Overlaps | 595 | 529 |
| Unoriented | 96 | 95 |
| Connectivity regions | 1 | 1 |
| Mesh status | Failed | Failed |
| AutoFix removed | - | 174 |

AutoFix execution succeeded, but the mesh did not pass the analysis gate.

## Failure signatures and root cause

- `61704 Internal Error`: unsafe/unstable COM operation or corrupted Synergy session; stop writes and recover from a saved copy.
- `ActiveX 429`: MCP and visible Synergy were in different Windows sessions/elevation contexts, or COM was not ready.
- `424 Object required`: unreliable VBScript `GetObject/Is Nothing` retry pattern; use checked 64-bit `CreateObject` in the interactive session.
- `MeshStatus=Running` for more than two hours with `synmesh.exe` CPU almost flat: inspection was exporting the active model during meshing. `Project.ExportModel` competed with `synmesh`.
- Remote worker restart of MCP can move it outside the visible Moldflow session. Start MCP from the same interactive desktop as Synergy.

## Decision rules

- IF Moldflow COM is 64-bit, THEN run all active-study VBS through 64-bit `cscript`, BECAUSE mixed-bitness probes are not authoritative.
- IF mesh status is `Running` or `Pending`, THEN inspect status only and never call `ExportModel`, BECAUSE export can block `synmesh`.
- IF `MeshStatus != Completed` OR intersections/overlaps/unoriented are nonzero at unsafe levels, THEN do not set a gate or start analysis.
- IF AutoFix changes elements, THEN save and remeasure; never treat `AUTOFIX_REMOVED` alone as success.
- IF MCP must control a visible study, THEN MCP and Synergy must run in the same interactive Windows session.

## Reproducible procedure

1. Start Synergy and MCP from the same interactive PowerShell session.
2. Verify bridge version, COM version 2010, project, active study, and exact study name.
3. Create a uniquely named `SaveAs` copy.
4. Verify intended mesh representation before meshing.
5. Start mesh once; during `Pending/Running`, skip UDM/gate export and poll at low frequency.
6. After completion, require positive nodes/triangles and inspect intersections, overlaps, unoriented, components, and aspect ratio.
7. Apply AutoFix only to the copy, save, then repeat the full quality inspection.
8. Select an explicit gate node only after the mesh passes.
9. Start Fill analysis only after material, process conditions, gate, and solver readiness are verified.

## Recovery and scope limits

- Backups exist beside deployed MCP server versions and as saved Moldflow copies.
- A hung `synmesh.exe` may be stopped only after PID, command line, target study, elapsed time, and low CPU delta prove the target.
- Proven: MCP connection, copy creation, mesh launch/monitoring, mesh diagnostics, AutoFix execution, save, and fail-closed gating.
- Not proven: accepted production mesh, automatic gate placement, or successful Fill analysis.
- Next experiment: import the repaired STL into a fresh Fusion study without using global Midplane mesh settings, mesh without concurrent export, then run the same quality gate.

## Provenance

- Date: 2026-07-17 to 2026-07-19 JST.
- Branch: `feat/mecha-autorig`.
- Key commits: `65bf3c3eb6`, `a3d5f356de`, `084d779c17`, `5034cd9208`.
- Incident: `INC-152`; Beads: `Clawdbot_Docker_20260125-h8dx`.
