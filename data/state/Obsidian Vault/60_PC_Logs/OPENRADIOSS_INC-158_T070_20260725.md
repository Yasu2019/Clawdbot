---
tags: [OpenRadioss, CAE, incident, 4mm]
incident: INC-158
trouble_id: T070
bd_key: Clawdbot_Docker_20260125-de46
updated: 2026-07-25
---

# OpenRadioss Lab 4mm urgent analysis launch failure

## Summary

- NG: the action returned HTTP 202 but exited before dispatch.
- Failure: missing `httpx`, including a transitive import.
- Fix gate: exact Python import, compile, three unit tests, and Red LAVIE health passed.
- Solver/VTK evidence remains mandatory before the active run can be called successful.

## QC工程表

| Step | Control point | Standard | Result |
|---|---|---|---|
| QC-01 | Portal/API | 8088 and 8777 respond | PASS |
| QC-02 | Child startup | No import traceback | PASS |
| QC-03 | Satellite route | `/healthz`=200 | PASS |
| QC-04 | Solver | Starter and Engine start | Pending |
| QC-05 | Physics | NORMAL TERMINATION, bounded DM/M and ERR | Pending |
| QC-06 | Artifact | VTK quality gate PASS | Pending |

## FMEA

| Failure mode | Effect | Cause | S/O/D | Countermeasure |
|---|---|---|---|---|
| Direct dependency missing | No dispatch | API Python lacks `httpx` | 8/6/2 | stdlib HTTP |
| Transitive dependency missing | First fix ineffective | downstream module imports at load | 8/5/3 | full import test |
| HTTP 202 false confidence | Operator assumes start | enqueue confused with execution | 7/6/5 | child-state evidence |
| Worker occupied | New run waits | serial worker lock | 5/4/2 | bounded polling |

## FTA / 5 Why

Top event: no 4mm result. The child exits before dispatch because its import
graph requires an absent package. Tests did not use the service interpreter,
and the API exposed enqueue rather than child-start state. Root cause is an
incomplete runtime dependency and observability contract.

## Fishbone / logical tree

- Machine: Red LAVIE worker is serial.
- Method: enqueue acknowledgment was treated as execution.
- Software: unnecessary third-party HTTP import.
- Measurement: no `dispatch_started` evidence.
- Environment: portal, API, and child use separate processes.

## Countermeasures

1. Use `urllib` for simple JSON health and metrics calls.
2. Test the transitive import graph with the exact API Python.
3. Keep worker polling bounded and avoid parallel CAE dispatch.
4. Require solver and VTK evidence before SUCCESS.

## Forbidden

- Declaring start from HTTP 202 alone.
- Installing a package when stdlib is sufficient.
- Bypassing the worker lock with a second solver.
- Reusing historical success as proof of the new run.

## Links

- `docs/INCIDENT_LOG.md` INC-158
- `data/workspace/memory/trouble_history.md` T070
- Beads `Clawdbot_Docker_20260125-de46`
