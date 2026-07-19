# Quality Incident: Stale Git index lock blocked backup commit

- Date: 2026-07-19 JST
- Goal: Commit only task RCA documents as a recovery point before Main LAVIE case creation.

## Observed facts

- Git failed with `Unable to create '.git/index.lock': File exists`.
- Lock path: `D:\Clawdbot_Docker_20260125\.git\index.lock`.
- Lock length: 0 bytes.
- Lock creation and modification time: 2026-07-19 13:45:47 JST.
- Two transient Git processes observed at 19:09:04 exited before command-line inspection completed.
- No lock deletion, commit, push, or LAVIE operation occurred.

## RCA (5 Whys)

1. `git add` could not acquire the index lock.
2. `.git/index.lock` already existed.
3. The lock is a zero-byte file more than six hours old.
4. A prior Git operation likely terminated without removing its lock.
5. The backup workflow did not preflight stale-lock state before attempting an index mutation.

## Decision rule

IF `.git/index.lock` exists, THEN do not delete it until its timestamp is old and no live Git process remains, BECAUSE removing an active lock can corrupt concurrent index operations.

## Countermeasure plan

1. Recheck that no Git-related process is active.
2. Resolve the lock path and verify it is exactly the repository's `.git\index.lock`.
3. Remove only that zero-byte stale lock.
4. Add and commit only the exact task document paths.
5. Verify commit contents before pushing.

## Verification

- Pass: lock removal targets one verified file; limited commit contains only task RCA documents; push succeeds.
- Fail: a Git process is active, lock timestamp changes, commit contains unrelated paths, or push fails.

## Recovery / rollback

- If activity reappears, stop and leave the lock untouched.
- No working-tree rollback is required because the failed command did not modify files.

## Scope limits

- The stale lock diagnosis does not explain which prior process originally created it.

## Web knowledge decision

- External search is unnecessary; local file metadata, process state, and Git's error establish the safe recovery condition.

## Next experiment

- Perform the guarded stale-lock removal and exact-path commit sequence.

## Provenance

- Local Git/process output, 2026-07-19 JST.
