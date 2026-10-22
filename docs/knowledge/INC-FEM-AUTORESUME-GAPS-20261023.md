# INC-FEM-AUTORESUME-GAPS-20261023

Unattended OpenRadioss corner/panel runs (INC-188 mesh study and panel crack runs) lost compute or risked losing it through gaps in the resume and completion-detection layer.
Recorded 2026-10-23 06:25 JST by the K10 Claude Code session. All machine values are HISTORICAL observations at the stated times (JST), not live telemetry.
Related: INC-THINKPAD-CONNECTIVITY-20261023 / THINKPAD_NLL14_COMMAND_REPAIR_20261023.md (the ThinkPad copy of finding C was repaired by another session), Beads Clawdbot_Docker_20260125-imme, -3bht, -cy62, -vm06.

## A. NL10 OOM kill with no autoresume (K10)
- Job: corner mesh study NL10 (10 um tetra, /NONLOCAL/MAT LE_MAX 3e-5), started 10-22 11:33 with a bare `eng.sh` (nt6) inside docker `clawstack-unified-openradioss-1`.
- Fact: docker VM dmesg "Out of memory: Killed process (engine_linux64_) anon-rss 20.1 GB"; status file `DONE rc=137` at 10-22 19:31; last cycle t=64.8/137.5 us. VM MemTotal 32 GB; P1r32f engine ~11.5 GB and ollama ~6 GB resident.
- Impact: ~10 h with no progress, noticed 10-23 05:41 only while answering an unrelated question.
- Root cause: memory over-commit of the docker VM by three large residents (allocating task at the time was ldconfig; which process grew is UNKNOWN). Contributing: NL10 had no resume task, so nothing retried or alarmed.
- Correction: an earlier hypothesis "conv.sh ran concurrently" was WRONG (conversion ran 19:45-19:50, after the kill).

## B. Completion detector accepted a killed run (K10)
- `post_nl10.sh` (task INC188_NL10_Post, 15 min) triggered on `grep ^DONE status_NL10`, which also matches `DONE rc=137`. At 19:50 it converted 20 frames and wrote NL10_RESULT.txt (ok=False row).
- Fix 10-23 06:0x: finished = newest .out has NORMAL TERMINATION and t >= end time on the run directory that is actually computing (now Main LAVIE). Negative test (run not finished): exit 0, no result written. Positive path not yet exercised (run not finished).
- Partial result kept as NL10_RESULT_partial_killed_t62us.txt; vtk f020 (written after the last restart) moved to vtk_NL10/run1_after_rst/. Nothing deleted.

## C. Autoresume deck generation truncated its own input (fleet)
- All copies of the OpenRadioss autoresume script (evo_autoresume.sh, ml_autoresume.sh, node_autoresume.sh) chose `SRC = newest *_00NN.rad` and then ran `sed ... $SRC > $NEW`. If deck N+1 already existed but restart N+1 did not (engine died before its first restart write), SRC == NEW and the shell truncated the deck to 0 B before sed read it. Every later tick logged `ABORT deck check` forever.
- Observed on ThinkPad NLL14 (decks 0002/0003 = 0 B, stalled 10-22 21:53 -> 10-23 06:09; repaired by the other session, see its note).
- Reproduced in isolation on K10 with the original lines (result: 0-byte deck). Fixed version tested on 4 cases: existing deck N+1 (uses deck N), empty decks 2 and 3 with restart 2 (uses deck 1, writes valid deck 3), normal case, no source deck (logs `ABORT no source deck`, writes nothing).
- Fix (`deckfix.py`): source = newest NON-EMPTY run deck other than NEW; write NEW.tmp then mv. Applied 10-23 06:3x to Red LAVIE /srv/fem-jobs/node_autoresume.sh (md5 ae05c988...), Main LAVIE ml_autoresume.sh (f1b05681...), Evo evo_autoresume.sh (77b20e6f...); originals kept as `*.before-deckfix-20261023`. Scan found no 0-byte decks under /srv on Evo/Main/Red. Evo P1r41f check after patch: alive -> exit 0, 1 engine.

## D. Evo resume tasks left disabled after a pause/reboot
- 10-22 21:32 Evo rebooted for a GPU reservation change (other session). P1r41f was stopped gracefully (21:41) and restarted in a NEW directory panel-P1r41f-resume-20261022-2201 by a one-shot task; all Clawstack_EvoPanel_*_AutoResume tasks were Disabled. A second reboot would not have resumed P1r41f.
- With user approval (10-23 04:10) Clawstack_EvoPanel_P1r41f_AutoResume was repointed to the 2201 dir and enabled; dry check: alive -> silent exit; crash -> run4 from 0003 restart. Ran once: result 0, still one engine, no new deck.

## E. Large transfer to Main LAVIE over Tailscale WAN path
- K10 192.168.3.x and Main LAVIE 192.168.5.x have no LAN route; Tailscale path is via the public address. A 1.3 GB scp reset after 16 min 40 s; 100 MB chunks failed 4 times; switched to 20 MB md5-checked chunks with per-chunk retry.
- Second defect in my transfer script: Git-Bash md5sum writes `hash *name`; grep for ` name` never matched, so finished chunks were re-sent. Fixed (`[ *]name`).

## F. Technical knowledge from the same checks (not incidents)
- Fine corner decks (14 um, 10 um): .out ERROR -73 % to -91 % from about 1 us. TH shows EXTERNAL WORK and PLASTIC WORK agree across all sizes, but INTERNAL ENERGY is about 1/4 of plastic work (physically impossible) -> IE output/accounting artifact on fine decks (cause UNKNOWN). Do not use .out ERROR or IE for these decks; use PW vs EXTERNAL WORK. Force (contact impulse) metrics unaffected.
- Itetra4=1 combined with /NONLOCAL/MAT (NLT20) is invalid: ruptures from 1.29 us, external work 4.5e-4 J vs 0.12 J for NL20. Itetra4=1 without nonlocal (MT1) behaved normally.
- Crack-path damage on panels is insensitive to the shear fracture strain (BIQUAD C2 0.6-1.6 gives D 0.445-0.446; triaxiality of new strain ~0.25) -> tensile-side fracture strains (C3/C4) control crack reproduction.

## Actual changes (all reversible)
Main LAVIE `%USERPROFILE%\.wslconfig` created with `[wsl2] memory=32GB` (none existed; user approved; WSL restarted with no job running; MemTotal 32.8 GB). Scripts listed above with backups. Task repoint on Evo. post_nl10.sh backup post_nl10.sh.before-remote-20261023.

## Open items
- NL10 resume on Main LAVIE as run2 (task Clawstack_MainLavie_NL10_AutoResume) after the chunked transfer is verified.
- K10 rule for >15 GB jobs vs P1r32f + ollama residency not yet defined.
- ssh alias `evo` missing from K10 ~/.ssh/config (use Suzuki@100.77.148.0); cause UNKNOWN.
- Real crash-to-resume test of the patched deck logic on a live run not performed.
