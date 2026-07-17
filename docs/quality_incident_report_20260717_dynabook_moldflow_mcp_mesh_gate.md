# Dynabook Moldflow MCP Mesh and Gate Automation Record

Date: 2026-07-17 JST  
Incident: INC-151  
Trouble ID: T066

## Goal

Operate Autodesk Moldflow Insight 2010 on Dynabook through MCP, preserve the original study, generate a Fusion mesh on `Moldflow_study (copy)`, and prepare explicit-node gate placement without automatically starting analysis.

## Context

- K10 Tailscale IP: `100.119.18.40`
- Dynabook: `DESKTOP-UOVCG4T`, Tailscale `100.98.133.40`
- MCP: `http://100.98.133.40:8765/mcp`
- Work root: `G:\moldflow_bridge\work`
- Moldflow: Insight 2010
- CPU: Intel Core i5-5200U, 2 cores/4 threads, observed 100% load
- Active study: `moldflow_study_(copy).sdy`

## Observed facts

| Evidence | Value |
|---|---|
| Live bridge | version 0.4.0, operations enabled |
| COM registry | CLSID LocalServer32 exists in 64-bit view only |
| COM state | Version 2010, active project/study, metric units true |
| Mesh request | 3.0 mm, `MESH_NOW_ERROR=0` |
| Live progress | Running; UI reached 30% |
| STL input | 272 nodes, 552 triangles |
| Geometry warnings | 4 non-manifold edges |
| Initial aspect ratio | max 293.2793, average 63.4481 |
| Safety state | original untouched; no gate; no analysis |

## Hypotheses

- Confirmed: initial delay is CPU-bound remeshing; system CPU reached 100% and Synergy remained responsive.
- Confirmed: immediate zero elements are an asynchronous intermediate state, not proof of mesh failure.
- Pending: final mesh quality may still fail because non-manifold edges and extreme input aspect ratios remain.

## Decision rules

1. IF Tailscale is `NoState`, THEN repair VPN before interpreting MCP health, BECAUSE ports and service identity are otherwise unreachable.
2. IF 8766 returns an unknown service contract, THEN use the separately verified 8765 bridge rather than weakening identity checks.
3. IF Synergy COM is registered only in 64-bit view, THEN execute write VBS with 64-bit cscript.
4. IF `MeshStatus=Running`, THEN poll and never start a duplicate mesh, BECAUSE `MeshNow(False)` is asynchronous.
5. IF final nodes/triangles are zero or diagnostics exceed limits, THEN do not set gate or start analysis.

## Procedure

1. Verify Tailscale peer and port 8765.
2. Initialize MCP and list tools.
3. Run server with `G:\moldflow_bridge\.venv\Scripts\python.exe` and bind `100.98.133.40`.
4. Verify remote SHA-256 and exact process identity.
5. Save and normally close any non-Automation Synergy GUI.
6. Start a 64-bit Automation session, then open the project and copy.
7. Confirm active project/study and metric units.
8. Call mesh tool once with expected canonical study name and 3.0 mm edge length.
9. Poll status until terminal; do not repeat while Running.
10. After quality PASS, choose an explicit node and call gate tool; inspect NDBC before analysis.

## Verification criteria

- Mesh pass: terminal completed status, nodes > 0, triangles > 0, one connectivity region, zero non-manifold/unoriented/intersection/overlap defects, declared aspect-ratio threshold met.
- Gate pass: exactly one intended NDBC 40000/40002/40003 at the reviewed node and coordinate.
- Analysis remains blocked until mesh and gate pass.

## Failure signatures

- `SSH tunnel did not open 127.0.0.1:18765`: VPN/tunnel unavailable.
- `Wrong service ... got unknown`: service contract mismatch.
- `No module named 'mcp'`: wrong Python interpreter.
- HTTP 421: bind/Host allowlist mismatch.
- COM 429/424: wrong registry view or non-Automation Synergy session.
- `MESH_STATUS=Running`, zero elements: asynchronous progress, not terminal failure.

## Recovery and rollback

- Never kill Synergy during meshing.
- Stop only the verified port-8765 owner.
- Restore one of `G:\moldflow_bridge\moldflow_mcp_server.py.bak_*` if deployment regresses.
- Git backup: `backup/moldflow-mcp-mesh-gate-20260717-123129`.
- Original study is preserved; all writes target the named copy.

## Scope limits

As of this record the mesh is still running. Final mesh quality, live gate placement, material assignment, solver completion, and fill KPIs are not proven.

## Next experiment

Complete the current mesh, capture final diagnostics, validate one explicit gate, then benchmark repaired STL versus third-party UNV/BDF/PAT mesh import on a scratch study.

## Provenance

- Source: live MCP responses and Dynabook PowerShell output, 2026-07-17 JST
- Code: `data/workspace/moldflow_bridge/moldflow_mcp_server.py`
- Tests: `data/workspace/moldflow_bridge/test_moldflow_mcp_server.py`
- Incident: INC-151; Trouble: T066
