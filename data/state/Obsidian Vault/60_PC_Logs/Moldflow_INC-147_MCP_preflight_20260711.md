---
tags: [moldflow, mcp, dynabook, incident, preflight]
incident: INC-147
trouble_id: T058
bd_key: Clawdbot_Docker_20260125-4pzh
updated: 2026-07-11
---

# Moldflow MCP preflight incident and controls

## Summary

- NG trial 1: `Test-NetConnection` exceeded the 20-second harness timeout.
- NG trial 2: TCP and HTTP bounded probes both showed Dynabook unreachable in five seconds.
- NG trial 3: local `pytest` was unavailable.
- OK trial: standard-library contract tests passed 2/2; Python and PowerShell syntax passed.
- OK trial: MCP 1.28.1 initialize/list-tools returned all three readiness tools.
- Impact: investigation delay only. Moldflow was not started and Dynabook was not modified.

## QC control plan

| Control point | Method | Acceptance | Reaction |
|---|---|---|---|
| Network | Bounded TCP + HTTP | Response within 5 seconds | Stop remote deployment |
| MCP package | Python/PowerShell parse | Zero syntax errors | Fix locally |
| Safety mode | Contract test | `analysis_enabled=false` | Block release |
| COM | 32-bit VBS probe | `[OK] CreateObject` | Do not add analysis tools |
| End-to-end | MCP initialize/list tools | K10 receives three tools | Diagnose Tailscale/firewall |

## FMEA

| Mode | Severity | Cause | Countermeasure |
|---|---:|---|---|
| Probe hangs | 4 | OS diagnostic exceeds budget | Five-second `TcpClient` bound |
| Node unreachable | 6 | Power/Tailscale/worker down | Stop and request node startup |
| Missing runner | 3 | Assumed pytest | Standard-library unittest |
| Guessed COM API | 9 | Moldflow 2010 contract unknown | Read-only gate and real COM probe |

## FTA / 5 Why

Top event: MCP readiness cannot be proven.

- Network branch: node offline OR Tailscale offline OR worker offline.
- Local validation branch: optional runner missing.
- Application branch: Synergy not started AND COM registration not yet verified.

Why chain: timeout -> slow diagnostic -> no explicit command budget -> availability not checked ->
no dependency-free first gate. Root cause is missing preflight discipline, not Moldflow physics.

## Fishbone / logical tree

- Machine: Dynabook availability unknown.
- Network: private Tailscale endpoint timed out.
- Method: first probe was too heavyweight.
- Software: pytest absent; MCP package intentionally installed only by deployment script.
- Safety: analysis remains disabled until 32-bit COM succeeds.
- Measurement: TCP, HTTP, MCP, and COM are separate gates.

## Countermeasures

1. Use bounded, dependency-free probes first.
2. Package locally without claiming remote installation.
3. Bind MCP to the Tailscale address and allow only K10 in Windows Firewall.
4. Expose only status, COM probe, and readiness gate initially.
5. Promote analysis tools only from observed Moldflow 2010 COM behavior.

Forbidden: unlimited waits, all-LAN exposure, guessed API calls, and dry-run success claims.

## Links

- `quality_incident_report_20260711_moldflow_mcp_preflight.md`
- `docs/INCIDENT_LOG.md` (INC-147)
- `data/workspace/memory/trouble_history.md` (T058)
- `data/workspace/moldflow_bridge/README.md`
