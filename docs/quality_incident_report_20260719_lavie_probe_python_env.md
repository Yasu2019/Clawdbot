# Quality Incident: LAVIE probe used wrong Python environment

- Date: 2026-07-19 JST
- Goal: Verify the Main LAVIE job worker before creating a new OpenFOAM resin-fill case.
- Context: K10 repository `D:\Clawdbot_Docker_20260125`; command run from PowerShell; target LAVIE endpoint is defined by the repository registry.

## Observed facts

- Command: `python scripts\cae_workload_router.py --probe-lavie-jobs --json`
- Result: exit code 1 before any network probe or remote write.
- Failure signature: `ModuleNotFoundError: No module named 'httpx'` at import time.
- No LAVIE job, OpenFOAM run, file upload, or case modification occurred.

## RCA (5 Whys)

1. The probe did not run because `httpx` could not be imported.
2. `httpx` was unavailable because the command used the system `python` environment.
3. The project virtual environment was not selected explicitly in the command.
4. The preflight invocation did not enforce or verify the expected interpreter.
5. The runbook command assumes a prepared Python environment but the current shell did not have it activated.

## Hypotheses

- The repository virtual environment at `.venv\Scripts\python.exe` contains `httpx`; this has not yet been verified.
- If it does not, dependency restoration will require a separate approved action.

## Decision rule

IF a repository networking script imports `httpx`, THEN invoke it with the repository virtual-environment Python and first verify `import httpx`, BECAUSE system Python dependency state is not guaranteed.

## Countermeasure plan

1. Read-only verify `.venv\Scripts\python.exe` exists and can import `httpx`.
2. Re-run the LAVIE job-worker probe with that exact interpreter.
3. Proceed only if the worker health gate passes.
4. Create a new disposable OpenFOAM case; do not overwrite the existing analysis.

## Verification

- Pass: interpreter import check returns exit code 0 and worker probe reports the LAVIE node online.
- Fail: missing interpreter/module, HTTP failure, authorization failure, or offline worker.

## Recovery / rollback

- No rollback is needed because no remote or analysis state changed.
- If later case creation fails, remove only the newly named disposable case after resolving its exact path; preserve all existing cases.

## Scope limits

- This incident proves only a local Python environment mismatch.
- It does not establish LAVIE online status or OpenFOAM readiness.

## Web knowledge decision

- External web search is not useful for this failure because the exact local import error and environment mismatch are sufficient to define the next bounded test.

## Next experiment

- Run `.venv\Scripts\python.exe -c "import httpx; print(httpx.__version__)"`, then use the same interpreter for the probe.

## Provenance

- Source: local command output on 2026-07-19 JST.
- Related runbook: `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`.
