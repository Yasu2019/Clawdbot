# Measure every registered PC before placing a calculation (2026-10-31)

Incident: INC-FLEET-DISPATCH-ALLPC-20261031-01. Observed 2026-10-31 07:23-07:40 JST by live SSH and the tailnet list.

What happened: a long calculation was queued behind another on one laptop while a 12-thread PC sat idle, because only 3 PCs from memory were compared. About 8 hours lost. A full check then found a second idle PC and the first laptop at 100 % load.

Root cause: the candidate list came from memory. A PC not on the list cannot be chosen and nothing reports the gap. Old notes were used as reasons for "busy".

Rule: before choosing a host, parallelism or a move, run `scripts/fleet_capacity_check.py`. It reads the list from `tailscale status`, keeps a row for every node, and exits 1 if an online computer could not be measured. Say "busy" only from a same-turn measurement. Put every PC in the report table.

Tool pitfalls found: Windows `LoadPercentage` read 2 % on a host with 39 % real load (use the `_Total` performance counter and look at the top process); a fixed solver name missed a custom binary name; `wsl --list` errors over SSH come back in UTF-16 and are not distribution names; a wedged WSL needs a per-call timeout.

Other lessons from the same work: Windows one-shot tasks with a clock time fire at that time, so give run-on-demand tasks a far-future date. A distance transform on a voxel mask reads half the real thickness of a wall two voxels thick; measure from the CAD surface. Python's and Git Bash's `/tmp` differ on Windows. Do not state that a stop or resume works until it has run.

Limits: the rule is text and does not mechanically block a dispatch. Effectiveness on a later dispatch is not yet shown.
