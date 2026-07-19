# Quality Incident Report: Dynabook Moldflow MCP preflight

Date: 2026-07-11 JST
Incident: INC-147
Beads: Clawdbot_Docker_20260125-4pzh

## Summary

Read-only connectivity checks did not reach `100.98.133.40:5683`. The first diagnostic
used `Test-NetConnection` and exceeded the 20-second harness limit. A later local test
attempt assumed `pytest`, which was not installed. No command reached Moldflow and no
Dynabook, Docker, database, or production file was modified by either failure.

## 5 Why

1. The first probe did not finish because `Test-NetConnection` performed a longer OS diagnostic.
2. It was selected without measuring its worst-case duration against the harness timeout.
3. The test run stopped because `pytest` was assumed rather than discovered.
4. Preflight dependencies and time budgets were not treated as explicit inputs.
5. The workflow lacked a dependency-free first gate for remote readiness work.

Root cause: diagnostic tools and test runners were selected before bounded availability checks.

## FMEA

| Failure mode | Effect | Control / countermeasure |
|---|---|---|
| Slow network diagnostic | Harness timeout | Use `TcpClient.ConnectAsync().Wait(5000)` |
| Remote node offline | Cannot deploy or verify | Prepare package locally; stop before claiming remote readiness |
| Missing Python test runner | Quality gate aborts | Use standard-library `unittest` |
| COM contract unknown | Unsafe guessed automation | Expose read-only probes; keep `analysis_enabled=false` |

## Web knowledge decision

No web search was used. Direct local evidence (timeout behavior, module discovery, registry,
and source inspection) was sufficient, and external information could not establish the live
state of the private Dynabook or its COM registration.

## Countermeasures and verification

- TCP and HTTP probes now use explicit five-second bounds.
- Tests use `unittest`; two contract tests passed in 0.049 seconds.
- Python compilation and PowerShell parser checks passed.
- MCP 1.28.1 initialize and list-tools smoke test passed with all three readiness tools.
- The MCP bridge is read-only and cannot start an analysis.
- Remote deployment and end-to-end MCP validation remain blocked until Dynabook/Tailscale is online.

Forbidden: unbounded probes, dependency assumptions, dry-run claimed as Moldflow success,
or analysis tools implemented from guessed COM method names.
