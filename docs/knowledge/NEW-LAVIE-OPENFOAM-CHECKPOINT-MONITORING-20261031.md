# New LAVIE OpenFOAM checkpoint and progress logging incident

Observed: 2026-10-31, JST. This note is a sanitized operational lesson; host addresses, account names, raw logs, engineering inputs and checkpoint data are excluded.

## What happened

A finite OpenFOAM validation ran three cases with four MPI ranks per case. The Windows-side wrapper output stopped changing while the in-guest solver logs continued to grow. Relying on the wrapper alone made progress and checkpoint status appear unknown. A direct, read-only WSL inspection found aligned native time directories across all ranks. All three solver logs later ended normally and the task returned result 0.

## What the evidence proves

The run completed normally and native OpenFOAM field outputs were present at the final recorded time and the immediately preceding write for all four ranks in each case. File size, timestamps and SHA-256 manifests were retained in the restricted project evidence store. This establishes output presence and rank alignment. It does not prove that the files can be accepted by a restart.

## Recovery hazard

The existing launcher claims `latestTime` restart but deletes prior case output at startup. Rerunning it could destroy the only retained output. Do not reuse that launcher against an existing case. A restart claim requires a non-overwriting acceptance run on an isolated copy with matching solver version, inputs and MPI layout.

## Recurrence controls

- Correlate task result, host processes, guest processes, in-guest solver log tail and native time-directory manifest; a stale wrapper alone is not a solver-status signal.
- Before unattended dispatch, capture input and run-script provenance, solver version, write cadence, rank layout and checkpoint hashes.
- Preserve the previous valid write while a newer write is produced.
- Reject any launcher that removes existing case output before proving its recovery path on a copy.
- Keep production dispatch gated until separate authorization and resource gates pass.

No task was stopped, no output was deleted, and no production dispatch was issued during this investigation.
