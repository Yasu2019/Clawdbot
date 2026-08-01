# INC-180: Moldflow Cool launched from SSH session 0

## Event / impact

- Date: 2026-08-02 JST
- Target: copied study `mf_minusx_cool_20260802.sdy`
- First launch: SSH `Start-Process cool.exe`, PID 1268, session 0
- Result: exited in under 10 seconds; only `synjmmsg.1268` (`1\t0`) was written;
  no `.oc1` or `.c2p`; source study remained unchanged.
- Impact: delayed the new Cool run by about two minutes. No existing study,
  Synergy process, or solver was stopped or overwritten.

## Root cause analysis

### 5 Why

1. Why were no Cool results produced? The session-0 launcher did not create an
   actual Cool analysis process.
2. Why? Moldflow 2010's solver/job-manager environment depends on the active
   interactive user session.
3. Why was session 0 used? SSH `Start-Process` was selected as the shortest
   launch path.
4. Why was that unsafe? The proven runbook already requires `schtasks /IT` for
   Moldflow/Synergy execution, but the launch path did not enforce it.
5. Why did detection work? The gate required `.oc1/.c2p`, a live process, and
   a non-empty analysis log rather than accepting a launcher PID.

### FTA / Fishbone

- Top event: no Cool artifacts.
- Session branch: SSH session 0 -> job-manager notification only.
- Method branch: launcher PID mistaken for solver PID.
- Measurement branch: stdout/stderr empty; artifact gate caught failure.
- Material/model branch: ruled out by the same copied SDY succeeding unchanged
  in session 1.

### FMEA

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Cool in session 0 | no result artifacts | `.oc1/.c2p` absent | `/IT` task in active session 1 |
| Launcher PID accepted | false RUNNING | process disappears, log empty | require analysis banner and result files |
| Retry overwrites original | evidence loss | path/hash audit | SaveAs copy and unique output stem |

## Correction and verification

Created unique interactive task `ClawMfMinusXCool20260802`, executing an
ASCII/CRLF command file in session 1. The unchanged copied SDY then produced:

- `.oc1`: 887,956 bytes
- `.c2p`: 188,150 bytes
- cycle time: 35.0000 s
- part surface T max/min/avg: 364.9521 / 326.1938 / 342.2514 K
- cavity surface T avg: 338.3401 K
- CPU: 8.81 s; exit code: 0

## Prevention rule / rollback / limits

IF running Moldflow 2010 CLI solvers remotely THEN use an interactive `/IT`
task in active session 1 and verify solver-specific artifacts BECAUSE an SSH
session-0 PID does not prove solver execution. Rollback is deletion of only the
new copied study/task after explicit approval; the original is untouched.
This Cool result supplies thermal reference values but does not prove
OpenFOAM equivalence or a fully coupled minus-X Flow+Pack+Cool+Warp solution.
