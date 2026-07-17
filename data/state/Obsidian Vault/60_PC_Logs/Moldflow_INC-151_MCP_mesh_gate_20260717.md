---
tags: [Moldflow, MCP, Dynabook, COM, mesh, CAE, incident]
incident: INC-151
trouble_id: T066
bd_key: dynabook-moldflow-mcp-mesh-gate-20260717
updated: 2026-07-17
---

# Moldflow INC-151: MCP mesh and gate automation

## Summary

- NG trials: VPN `NoState`, incompatible 8766 contract, wrong global Python, localhost/421 bind policy, COM 429, and premature empty-mesh judgment.
- OK trial: 8765 MCP connected, 64-bit Automation session verified, active copy matched, 3.0 mm mesh accepted with error 0, visible progress reached 30%.
- Impact: first proven MCP-triggered real Moldflow 2010 mesh operation on Dynabook. Original study preserved. Gate and analysis not yet executed.

## QC工程表

| Process | Control item | Method | Acceptance | Reaction |
|---|---|---|---|---|
| Network | VPN and service identity | Tailscale + MCP initialize | Dynabook online; correct bridge | Stop before COM |
| Runtime | Python/bind | process path and Host | bridge venv; Tailscale IP | Restart verified PID only |
| COM | bitness/session | registry + state probe | 64-bit, Version 2010, active study | Save/close GUI; start Automation |
| Study | identity | canonical name gate | exact intended copy | Fail before mutation |
| Mesh | status/quality | MCP poll + diagnostics | completed, elements > 0, defects 0 | No duplicate start; repair mesh |
| Gate | node/NDBC | explicit node + UDM inspect | reviewed node, one gate | Remove/replace on mismatch |
| Analysis | authorization | readiness gate | mesh and gate PASS | Keep blocked |

## FMEA

| Failure mode | Effect | Cause | Control | Countermeasure |
|---|---|---|---|---|
| Wrong service/port | unsafe commands or false health | 8765/8766 coexist | service identity | never accept listener alone |
| COM 429 | operation cannot start | wrong bitness/non-Automation GUI | registry/session probe | 64-bit Automation session |
| Duplicate mesh start | corruption/waste | Running treated as failure | status gate | one start, bounded polling |
| Wrong study write | original damaged | display/SDY name mismatch | canonical identity | copy-only fail-closed |
| Bad mesh accepted | invalid flow result | non-manifold/high AR | diagnostics | block gate/analysis |

## 5 Why

1. Why could MCP not mesh? COM creation and transport repeatedly failed.
2. Why? VPN, service version, interpreter, bind policy, and COM were conflated.
3. Why did COM fail? Synergy was registered in 64-bit view and normal GUI rejected automation.
4. Why was a successful start reported as empty? `MeshNow(False)` returned before meshing completed.
5. Why was this not known? The bridge had no real active-copy mesh contract or asynchronous live trial.

## Fishbone

- Machine: i5-5200U, 2 cores, CPU 100%.
- Method: synchronous assumption for asynchronous MeshNow.
- Material/data: STL has 4 non-manifold edges and extreme aspect ratio.
- Software: Moldflow 2010 COM view and singleton Automation behavior.
- Network: Tailscale state and two MCP routes.
- Measurement: API reports zero elements until mesh publication.

## Countermeasures

- Preserve separate network, identity, runtime, COM, study, mesh, gate, and analysis gates.
- Use venv Python and Tailscale-IP bind.
- Use 64-bit cscript for new write tools.
- Treat Running as progress and never duplicate the mesh.
- Prefer repaired STL or benchmarked third-party mesh for future speed and quality.

## Forbidden

- Do not run `check_synergy_com.vbs` during meshing.
- Do not start a second mesh while status is Running.
- Do not set a gate before terminal mesh quality PASS.
- Do not claim gate or analysis success from tool availability alone.
- Do not modify the original study.

## Links

- [Incident log](../../../docs/INCIDENT_LOG.md)
- [Detailed report](../../../docs/quality_incident_report_20260717_dynabook_moldflow_mcp_mesh_gate.md)
- [Trouble history](../../workspace/memory/trouble_history.md)
- [MCP server](../../workspace/moldflow_bridge/moldflow_mcp_server.py)
