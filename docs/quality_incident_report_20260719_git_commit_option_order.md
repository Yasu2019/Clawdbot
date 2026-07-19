# Quality Incident: Path-limited commit used invalid option order

- Date: 2026-07-19 JST
- Goal: Commit only six task RCA documents before Main LAVIE case creation.

## Observed facts

- Guarded removal of the verified stale `.git/index.lock` succeeded.
- Six exact task documents were added to the index.
- Commit failed with `pathspec '-m' did not match any file(s) known to git`.
- No commit, push, remote upload, or OpenFOAM operation occurred.

## RCA (5 Whys)

1. Git interpreted `-m` as a pathspec.
2. `-m` appeared after the `--` end-of-options marker.
3. Everything after `--` is parsed as a path.
4. The command placed the message option after the dynamically expanded path list.
5. The limited-commit command was not syntax-checked with options before the separator.

## Decision rule

IF a Git command uses `--` to terminate option parsing, THEN place every option, including `-m`, before `--`, BECAUSE all later arguments are treated as paths.

## Countermeasure plan

1. Add this seventh exact RCA path.
2. Run `git commit -m <message> --only -- <seven exact paths>`.
3. Verify `HEAD` contains exactly those seven paths.
4. Push `feat/mecha-autorig`.
5. Confirm unrelated index and working-tree entries remain present and uncommitted.

## Verification

- Pass: one commit with exactly seven named RCA documents and successful remote push.
- Fail: unrelated path in commit, syntax error, or push failure.

## Recovery / rollback

- If commit fails, leave the index intact and correct only the invocation; do not reset the shared dirty worktree.

## Scope limits

- This incident concerns Git CLI syntax only and does not affect STL or LAVIE state.

## Web knowledge decision

- External search is unnecessary because the Git parser error and local command order fully establish the cause.

## Next experiment

- Execute the corrected option ordering and inspect the resulting commit before push.

## Provenance

- Local Git output, 2026-07-19 JST.
