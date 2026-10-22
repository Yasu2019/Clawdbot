# INC-FEM-AUTORESUME-GAPS-20261023: reusable knowledge card

Evidence observed 2026-10-22 19:31 to 2026-10-23 06:30 JST on K10, Evo, Main LAVIE, Red LAVIE, ThinkPad. Historical, not live.

1. A long FEM run without a resume task is not "unattended work". An OOM-killed OpenRadioss engine (rc=137) sat idle ~10 h because it was started with a bare script.
2. Completion detectors must test solver termination, not wrapper text: "DONE rc=137" matched `grep ^DONE`. Use NORMAL TERMINATION in the newest .out AND final time >= end time. Test the detector on a killed run.
3. Never generate a file by `cmd $SRC > $NEW` when SRC can equal NEW: the shell truncates first. OpenRadioss autoresume picked the newest deck as template; when deck N+1 existed without restart N+1, it zeroed the deck and aborted forever. Use a non-empty template different from the target, write to a temp file, then rename. Check every copy of a script family, not just the host where it failed.
4. After any planned pause or reboot by any session, re-check resume tasks: enabled, and pointing at the directory where the engine actually runs.
5. Memory: a 32 GB docker VM cannot hold a 20 GB engine next to an 11.5 GB engine and a 6 GB LLM service. Compare target MemAvailable with the job's RSS before dispatch.
6. Over a Tailscale WAN path, multi-GB scp resets; send md5-checked chunks with per-chunk retry. Git-Bash md5sum prints `hash *name`.
7. OpenRadioss fine tetra decks may report a large .out energy ERROR while EXTERNAL WORK and PLASTIC WORK agree; internal energy below plastic work indicates an accounting artifact, not lost energy. Itetra4=1 with /NONLOCAL/MAT gave immediate unphysical rupture; do not combine.
No credentials, raw logs or private data in this card.
