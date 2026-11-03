# INC-MOLD-MOVE-TORN-CKPT-20261103: a moved run started from zero on a torn restart file

Observed 2026-11-03 09:57 JST. Near miss, no calculation lost.

What happened: a run was moved between hosts. The file copy failed with a connection reset; the script printed the error and queued the run anyway. The solver skipped the unreadable restart files, as designed, and started from step 0 with no error. Noticed within a minute from the output.

Lesson: a fallback that works silently can hide a failed step. Make the next step conditional on the previous one. A move is complete only when the target compares the whole-file hash and the log shows the expected step.

Also: a host with a one-job limit had a second job for hours. Read the running-job list before dispatch; free RAM is not enough.

Change: chunked copy with retries; queue only on a hash match. This lives in a one-off script, not yet in the tooling.
