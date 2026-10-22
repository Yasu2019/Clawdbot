# INC-FEM-AUTORESUME-GAPS-20261023: FMEA / FTA / QC process chart / Control Plan (draft revision 1)

Canonical incident: INC-FEM-AUTORESUME-GAPS-20261023.md. Revision 1, 2026-10-23 06:30 JST, reason: initial capture.
S/O/D and RPN are NOT assessed (no approved scoring criteria). No named owner or formal approval is claimed. Thresholds below are the values already used by the scripts or approved by the user, not new limits.

## FMEA
| # | Failure mode | Effect | Cause (status) | Prevention | Detection | Action / validation | Residual |
|---|---|---|---|---|---|---|---|
| F1 | Long FEM run started without a resume task | Killed run idles until a human looks (NL10: ~10 h) | Bare eng.sh launch (confirmed) | Every unattended run gets an autoresume task before it is reported as running | Fleet check counts engines vs registered tasks | NL10 being moved under Clawstack_MainLavie_NL10_AutoResume; validation pending | Other bare launches may exist; no fleet-wide audit yet |
| F2 | Host/VM memory over-commit kills the largest engine | Lost progress since last restart | 3 large residents in 32 GB docker VM (confirmed); growth source UNKNOWN | Check free memory vs job RSS before dispatch | dmesg OOM lines, status rc=137 | Moved NL10 to a 32 GB WSL host; K10 rule not defined | Recurrence possible on K10 |
| F3 | Completion detector treats a killed run as finished | Partial result reported as final | Trigger matched "DONE" text, not solver termination (confirmed) | Require NORMAL TERMINATION and t >= end | Result row ok=False; compare t with end | Fixed; negative test passed; positive pending | Other post scripts not audited |
| F4 | Resume script truncates its own deck input | Permanent ABORT loop; run never resumes | SRC == NEW redirection (confirmed, reproduced) | Non-empty source != NEW; temp file + mv | history "ABORT deck check" repeated; 0-byte decks | Fixed on Evo/Main/Red; 4-case unit test passed; ThinkPad fixed separately | Live crash-to-resume not exercised |
| F5 | Resume tasks disabled after a pause/reboot | Second reboot would not resume | Other session disabled tasks and moved run dir (confirmed) | After any pause, re-enable/repoint tasks to the live dir | Task State + Arguments vs engine cwd | P1r41f repointed and verified (silent exit while alive) | Depends on sessions coordinating |
| F6 | Large file transfer resets over WAN path | Dispatch delayed | No LAN route Main<->K10; Tailscale WAN resets (confirmed symptom, cause of resets UNKNOWN) | Chunked md5-verified transfer with retry | Per-chunk md5 | 20 MB chunks running | Throughput ~1 MB/s |
| F7 | Integrity check helper never matches | Endless resend, no progress | md5sum '*name' format (confirmed) | Test helper on one chunk before batch | Output shows no "ok" lines | Fixed and tested on part.000 | — |

## FTA
Top event: unattended FEM run makes no progress without an alarm.
- OR G1 run stops: OOM kill (confirmed, A) / host reboot (confirmed for Evo, ThinkPad) / solver error (not observed).
- AND G2 nothing restarts it: no resume task (confirmed, A) OR task disabled/pointing at old dir (confirmed, D) OR resume logic aborts (confirmed, C).
- AND G3 nobody is told: completion detector false positive (confirmed, B) OR no stall alarm on run progress (confirmed gap; open).
Unresolved branches: why memory grew at 19:31 (UNKNOWN), why WAN transfers reset (UNKNOWN), reboot cause on ThinkPad (UNKNOWN, see other incident).

## QC process chart (dispatch and resume of unattended FEM runs)
1. Dispatch gate: free memory on the target >= job RSS + margin; record engine sha, nt, deck, end time. Reject if no autoresume task can be registered.
2. Register gate: autoresume task points at the actual run dir; run it once while the engine is alive -> must exit silently with engine count unchanged.
3. Checkpoint gate: first restart file written with plausible size and timestamp before reporting "running".
4. Resume gate: deck generated from non-empty template != target; deck header /RUN/<name>/<N+1>; verify native "RESTART" acceptance in the new .out.
5. Completion gate: NORMAL TERMINATION and t >= end in the newest .out of the live dir; then post-processing.
6. Pause/reboot gate: after any planned stop, re-check every resume task (State, Arguments, cwd of engine).
Records: autoresume.history per run dir, trouble_history.md, this incident ID. Escalation: hold and report to the user when a gate fails; do not force-start.

## Control Plan
| Characteristic | Method | Timing | Acceptance | Reaction | Evidence |
|---|---|---|---|---|---|
| Resume task coverage | List engines per node vs registered autoresume tasks | At dispatch and after each reboot/pause | Every engine has an enabled task with matching dir | Register/repoint before reporting | Task Arguments + engine cwd |
| Deck generation integrity | Unit test (4 cases) + header check in script | On every script change; every resume | Non-empty deck, correct /RUN number | Script logs ABORT and writes nothing | dtest output, autoresume.history |
| Completion detection | NORMAL TERMINATION + end time | Every post tick | Both true | No result written | post logs |
| Memory headroom | MemAvailable vs job RSS | Before dispatch | Headroom above job RSS (limit not yet set for K10) | Dispatch elsewhere or wait | meminfo snapshot |
| Transfer integrity | md5 per chunk and whole file | Every transfer | All match | Resend chunk; abort on repeated failure | md5 lists |
Effectiveness: F3/F4/F7 verified by tests; F1/F2/F5 verified only for the specific runs; live crash-to-resume not demonstrated. Documents alone do not prove the faults are corrected.
