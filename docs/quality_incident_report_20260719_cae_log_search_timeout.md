# Quality Incident: CAE log search timed out

- Date: 2026-07-19 JST
- Goal: Locate the latest Main LAVIE resin-fill trial without changing an existing case.
- Context: Repository `D:\Clawdbot_Docker_20260125`; read-only ripgrep search; 20-second command limit.

## Observed facts

- A repository-wide filename/content search for CAE trial logs exceeded 20 seconds.
- Exit code: 124.
- No remote call, OpenFOAM execution, upload, or file modification occurred during the failed search.

## RCA (5 Whys)

1. The command failed because it reached the timeout.
2. It reached the timeout because content search covered the full repository.
3. The repository contains large generated, archive, and data trees.
4. The search did not constrain itself to the known CAE workspace and dispatch scripts.
5. The initial lookup optimized for recall rather than a bounded preflight query.

## Hypotheses

- The required run path can be obtained from the dispatch script, worker API, or a narrowly scoped workspace log without a full-repository scan.

## Decision rule

IF a repository contains large generated/data trees, THEN search known canonical paths first and exclude archives/build outputs, BECAUSE global content searches can exceed the bounded diagnostic window.

## Countermeasure plan

1. Inspect only `scripts/k10_satellite_cae_dispatch.py`, the LAVIE worker API contract, and canonical CAE workspace configuration.
2. Use filename-only enumeration before any content search.
3. Keep each read-only query bounded to a small path set.

## Verification

- Pass: identify the disposable-case input/output path and supported payload fields within 10 seconds per query.
- Fail: another timeout or ambiguous case target.

## Recovery / rollback

- None required; the failed operation was read-only.

## Scope limits

- This failure does not indicate a LAVIE or OpenFOAM problem.

## Web knowledge decision

- External search is not useful because the issue is local repository search scope and the canonical local scripts are authoritative.

## Next experiment

- Read the dispatcher and worker request handler directly, then use their declared paths and payload schema.

## Provenance

- Local command output, 2026-07-19 JST.
- Related runbook: `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`.
