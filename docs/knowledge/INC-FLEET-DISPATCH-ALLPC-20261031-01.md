# INC-FLEET-DISPATCH-ALLPC-20261031-01: calculation placed without measuring every registered PC

Observed: 2026-10-31 07:23-07:40 JST (Asia/Tokyo). Source: live SSH / `tailscale status --json` from K10 (`scripts/fleet_capacity_check.py`). Reported by the user.

## Summary

Two long 3D fill calculations (project-confidential geometry, details in the restricted project note) were queued one after the other on Red LAVIE on the evening of 10-30. The agent compared only K10, Red LAVIE and EVO. Main LAVIE was idle and never looked at. Case B started on Main LAVIE at 07:25 JST on 10-31, after the user asked about it, about 8 hours later than it could have (first run of A began about 23:10 on 10-30).

## Facts (live, 2026-10-31)

| Time JST | Observation | Source |
|---|---|---|
| 07:23 | Main LAVIE CPU 6 %, about 28 GB free, no job | SSH |
| 07:33 | tailscale lists 15 nodes; the agent had been reasoning about 3-4 | `tailscale status --json` |
| 07:35 | G3 load 4/0/2 %, 11.1 GB free, 4 threads: also idle | fleet check |
| 07:35 | Red LAVIE 100/100/100 %, one 6-rank run plus 2 pressure workers on 8 threads | fleet check |
| 07:35 | Vivobook load 16/6/0 %, its WSL did not answer within 20 s while FEM task shows Running; D: 0 GB free, F: 1.5 GB | fleet check, SSH |
| 07:35 | New Red LAVIE WSL not readable over SSH (known); a job owned by another session is running | fleet check, other session's note |
| 07:39 | Main LAVIE 6 ranks at 99.9 %, 175 steps in 805 s; Red LAVIE t=0.385 s after 8.5 h | SSH |

## Impact

About 8 hours of Case B calculation time lost. Red LAVIE's run was slowed by the workers sharing its cores. The earlier answer to the user listed reasons for other PCs from old observations (ThinkPad and others) and left Main LAVIE out of the table.

## Root cause (verified from the session's own actions)

The candidate list came from the agent's memory instead of the registry. A PC that is not on the list cannot be selected and nothing reports its absence. No step required a check of all PCs before dispatch. Reasons such as "busy" were carried over from older notes without a fresh measurement, against the existing Current-State Freshness Rule.

Not known: whether Vivobook's WSL timeout is a fault or a transient. Owner of that run is a separate session; not touched, not diagnosed further here.

## Related failures in the same work (10-30 to 10-31)

1. **Scheduled-task misfire.** One-shot tasks registered with `/SC ONCE /ST 23:59` fired at 23:59 and started duplicate solvers (18 processes). Duplicates were killed; saved data was checked and unaffected. Control: `/SD 2030/01/01` for run-on-demand tasks; process-count alarm in the watcher, tested on both sides.
2. **Thickness read from the voxel mask.** A distance transform on voxels reported half the real wall when the wall is two voxels thick (1.2 mm read as 0.6), so pressures were about 4 times too high. A match with the machine pressure had been reported as a success and was retracted. Control: thickness from the CAD surface; plate test; independent 2V/S check.
3. **Stale temp path.** Python's `/tmp` and Git Bash's `/tmp` are different folders on Windows; a stale plan was deployed and every case exited 2. Control: plans live in the repo's artifacts folder.
4. **"Pause available" stated before it ran.** The resume script never ran because `set -u` broke the OpenFOAM environment; the claim was false until tested. Control: state a capability only after running it.
5. **Measurement tool's first version** (this incident's own fix) used `LoadPercentage`, which read 2 % on a host with 39 % real load, and a fixed `engine_linux` pattern that missed `engine_k10`. Both fixed before use in a decision; found by comparing a host's load with its largest process.

## Actual changes

- `scripts/fleet_capacity_check.py` and `scripts/test_fleet_capacity_check.py` (host list from tailscale; unmeasured online PC keeps a row and exits 1).
- Global rule section 0-d in `C:\Users\yasu\.claude\CLAUDE.md`.
- Case B moved to Main LAVIE (07:25). Three not-yet-started worker cases sent to G3 under `D:\m76` (own task, own venv; nothing else on G3 changed).

## Verification and limits

- Tool tested both ways: a healthy fleet exits 0; an unregistered online PC and an unreachable PC stay listed and exit 1. Live run: 15 of 15 nodes listed.
- **The rule is text. It does not mechanically stop a dispatch.** It works only if the agent runs the tool first. Effectiveness is not yet demonstrated by a later dispatch.
- `muse` (blank OS, no ping reply) has no known login and is shown as NO_LOGIN_KNOWN.

## Open items

- Vivobook WSL timeout and full disks: for the owning session or the user.
- Whether a pre-dispatch hook should enforce the rule: not done, needs a reliable way to recognise a dispatch.

Controls: `INC-FLEET-DISPATCH-ALLPC-20261031-01-controls.md`. Shared card: `INC-FLEET-DISPATCH-ALLPC-20261031-01-card.md`.
