# Quality Incident: Stale Git HEAD lock blocked limited commit

- Date: 2026-07-19 JST
- Goal: Create and push a path-limited recovery commit before Main LAVIE case work.

## Observed facts

- The corrected limited commit invoked repository hooks.
- A Beads hook exported 195 issues and 170 memories to `.beads/issues.jsonl`.
- Git then failed with `cannot lock ref 'HEAD'` because `.git/HEAD.lock` existed.
- `HEAD.lock` is zero bytes and dated 2026-07-19 13:49:57 JST.
- No Git-related process remained during inspection.
- No commit or push occurred.
- `.beads/issues.jsonl` is outside the intended limited commit and must remain uncommitted by this task.

## RCA (5 Whys)

1. Git could not update `HEAD` because `HEAD.lock` already existed.
2. The lock is a zero-byte stale file from an earlier interrupted Git operation.
3. The previous recovery checked `index.lock` but not all Git transaction lock files.
4. Commit hooks ran before ref update and modified Beads state.
5. The preflight did not verify both `index.lock` and `HEAD.lock` before invoking commit.

## Decision rule

IF a repository has evidence of interrupted Git operations, THEN check both index and ref lock files before committing, and remove a lock only when it is old, zero-byte, resolved to the exact repository path, and no Git process is active.

## Countermeasure plan

1. Recheck absence of Git processes.
2. Verify `.git\HEAD.lock` is the exact stale zero-byte file and remove only it.
3. Add the eighth exact RCA document.
4. Re-run the path-limited commit with options before `--`.
5. Verify the resulting commit contains only the eight RCA paths; specifically exclude `.beads/issues.jsonl`.
6. Push only after verification.

## Verification

- Pass: commit contains exactly eight RCA documents, excludes Beads, and pushes successfully.
- Fail: active Git process, changing lock timestamp, unrelated committed path, or push error.

## Recovery / rollback

- Do not reset or restore `.beads/issues.jsonl`; it may contain concurrent user/automation state.
- Leave unrelated index and worktree changes untouched.

## Scope limits

- The originating process for the stale `HEAD.lock` is not proven.

## Web knowledge decision

- External search is unnecessary because local lock metadata and process state determine the safe action.

## Next experiment

- Guarded removal of only stale `HEAD.lock`, followed by exact-path commit verification.

## Provenance

- Local Git, hook, file-metadata, and process output on 2026-07-19 JST.
