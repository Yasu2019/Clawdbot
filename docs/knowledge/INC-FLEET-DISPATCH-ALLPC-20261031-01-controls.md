# INC-FLEET-DISPATCH-ALLPC-20261031-01: FMEA / FTA / QC process chart / Control Plan

Draft revision 1, 2026-10-31. Reason: new incident. S/O/D and RPN are not assessed: no scoring criteria apply here. Owners are roles, no named owner or formal approval is implied. Thresholds below are those already stated in the global rules, or marked as this tool's definition.

## FMEA (unscored)

| Failure mode | Effect | Cause | Prevention | Detection | Action owner | Validation | Residual risk |
|---|---|---|---|---|---|---|---|
| Idle registered PC not considered at dispatch | Hours of calculation lost; one PC overloaded | Confirmed: candidate list from memory, no all-PC step | Rule 0-d; `fleet_capacity_check.py` before dispatch | Tool exit 1; every row in report table | Agent | Tool tests pass both ways; live 15/15 listed | Rule is text; agent can skip it |
| "Busy" stated from an old note | Wrong placement; misleading answer | Confirmed: old observation reused | Same-turn measurement only | User or reviewer sees no timestamp | Agent | Not yet shown on a later dispatch | Same |
| Measurement misreads the host | Idle host looks busy or the reverse | Confirmed: `LoadPercentage` 2 % against real 39 %; pattern missed `engine_k10` | Perf counter `_Total`; `engine_` pattern; show top processes beside load | Compare load with the top process | Agent | Re-run: EVO 43 %, matches vmmem 1254/3200 | Other solver names may still be missed |
| One-shot task fires at a near clock time | Duplicate solvers | Confirmed: `/SC ONCE /ST 23:59` | `/SD 2030/01/01` | Watcher alarm over expected process count | Agent | Alarm tested both sides | Other hosts' tasks use their own pattern |
| Local thickness from voxel mask | Pressure about 4 times too high; false match reported | Confirmed: half-thickness at 2-voxel walls | Thickness from CAD surface | Plate test; 2V/S check | Agent | Plates within 2.1 % | Local features not plate-like |
| Plan read from a different `/tmp` | All cases exit 2 | Confirmed: Python and bash `/tmp` differ | Repo artifacts folder | Check case return codes | Agent | Regenerated plan ran | Low |
| Capability claimed before running it | User relies on a stop that does not exist | Confirmed: pause script never ran | Run first, then state | Evidence with the claim | Agent | Pause/resume run 23:08-23:10 on 10-30 | Agent discipline |

## FTA

Top event: a long calculation waits or runs slowly while a suitable PC is idle.

- OR 1: the idle PC is not considered.
  - AND: list made from memory (confirmed) / no gate requires the whole list (confirmed).
- OR 2: the PC is considered and wrongly rejected.
  - Old observation used as a reason (confirmed).
  - Measurement misreads load (confirmed in the tool's first version, fixed before a decision used it).
- OR 3: the PC cannot be reached or used (not the cause here).
  - WSL unreadable over SSH: New Red LAVIE (known), Vivobook timeout (cause UNKNOWN, unresolved branch).
  - Missing Python packages: G3 (found and resolved with a venv).

## QC process chart

| Step | Control gate | Method | Criteria | Record | Escalation |
|---|---|---|---|---|---|
| Choose host, parallelism, or move | Before dispatch, same turn | `fleet_capacity_check.py` | Exit 0, or each unmeasured PC explained | Table in the report | Tell user which PC could not be measured |
| Dispatch | After start | Solver count and progress on the target | Expected process count, time advancing | Progress lines with JST time | Stop own duplicates, keep the earliest |
| Report | Before sending | Table has every registered PC | No PC missing; states carry same-turn values | The report | Correct the report |
| Long loop | Every tick | Same tool | Idle PC with waiting work is used | Tick note | Move waiting work |

## Control Plan

| Characteristic | Method | Frequency | Acceptance | Reaction | Owner | Evidence |
|---|---|---|---|---|---|---|
| All registered PCs measured before dispatch | Tool output | Each dispatch decision | Every tailnet node has a row; online computers MEASURED or a stated reason | Do not decide until read; report unmeasured | Agent | Tool output, `--json` file |
| Tool still detects gaps | `test_fleet_capacity_check.py` | Each change to the tool | All PASS | Fix before use | Agent | Test output |
| Rule effectiveness | Review later dispatches for a preceding fleet check | Next dispatches | Check precedes each one | Add enforcement | Agent; user decides on a hook | Session records |

Implementation check: tool and rule exist and are tested. **Effectiveness on a real later dispatch is not yet verified.** This document does not by itself prove the fault is corrected.
