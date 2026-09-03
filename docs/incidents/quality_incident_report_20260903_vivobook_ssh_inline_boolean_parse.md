# Vivobook SSH inline Boolean parse incident, 2026-09-03

## Goal

Read-only confirmation that the new Vivobook OpenFOAM case path was free and no solver process already owned it.

## Context

- Controller: `NucBox_K10`, Windows PowerShell 5.1
- Target: Vivobook `mhn15` (`100.65.182.27`), Ubuntu 22.04 under WSL
- Intended case: `/opt/openfoam_runs/box_repro_v003_20260903`
- Constraint: preserve all existing robot-ML, OpenRadioss, DXF, and other unrelated workloads.

## Observed facts

- PowerShell rejected the command before SSH started.
- Failure signature: `The token '&&' is not a valid statement separator in this version.` and the same error for `||`.
- No remote command ran, no process changed, and no case data was created.
- A subsequent binary tar-stream attempt also failed before deployment: Windows SSH remote-command re-parsing reduced the compound command to `mkdir` without an operand; local `tar.exe` then reported `Write error` after the SSH consumer exited.
- The exact target remained absent after the first audit, and no solver was started.
- Web search was not used because this is a deterministic local parser/quoting failure with a known safer implementation already proven by `vivobook_openfoam_resume_watchdog.py`.

## Hypotheses

- Confirmed root cause: nested quoting ended the intended remote command string early, exposing Bash Boolean operators to Windows PowerShell 5.1.
- Confirmed transport extension: even when invoked through Python, the Vivobook Windows SSH server reparses the command before `wsl.exe`, so compound `bash -lc` arguments are not a safe binary-stream deployment channel.

## 5 Whys

1. The audit did not run because PowerShell raised a parser error.
2. PowerShell saw `&&` and `||` as local syntax.
3. The nested quote boundary did not preserve the entire Bash program as one SSH argument.
4. A complex inline command was used across PowerShell, Windows SSH, `wsl.exe`, and Bash.
5. The established stdin-bytes transport used by the resume watchdog was not reused for this audit.

## Decision rule

IF a Vivobook operation needs compound Bash syntax, THEN send an LF-normalized script through SSH stdin to `wsl.exe ... bash -s`, BECAUSE inline quoting crosses four parsers and is not reliable in Windows PowerShell 5.1.

IF case files must be transferred, THEN create a bounded local tar artifact, copy it with SCP to an exact Windows path, and use the stdin-script channel to validate and extract it, BECAUSE piping tar through a compound Windows SSH command can close the consumer early and corrupt the transfer.

## Procedure

1. Construct SSH arguments as a PowerShell array.
2. Store the Bash program in a literal here-string or existing `.sh` file.
3. Encode as UTF-8 bytes and normalize CRLF to LF.
4. Pipe bytes to `wsl.exe -d Ubuntu-22.04 -- bash -s --`.
5. Require hostname, exact case-path, and PID/CWD evidence before mutation.
6. For file deployment, verify local and remote archive hashes, extract to a new exact case path, and remove only the named temporary archives in a `finally` cleanup.

## Verification

- Pass: remote stdout contains hostname `mhn15`, an exact `TARGET_FREE` or `TARGET_EXISTS` verdict, process evidence, and disk evidence.
- Fail: local parser error, SSH nonzero exit, wrong hostname, or ambiguous target state.

## Recovery / rollback

No rollback is required because execution stopped before SSH. Preserve this report and retry only with stdin-script transport.

## Scope limits

This incident proves only a controller quoting failure. It says nothing about Vivobook solver readiness or case validity.

## Next experiment

Transfer a bounded archive by SCP, verify its hash, and extract it using stdin-script transport only if the exact target remains free.

## Provenance

- Date: 2026-09-03 JST
- Related: `scripts/vivobook_openfoam_resume_watchdog.py`
- Bead: `Clawdbot_Docker_20260125-hggr`
