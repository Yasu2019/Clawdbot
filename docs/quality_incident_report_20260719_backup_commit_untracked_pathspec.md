# Quality Incident: Backup commit rejected untracked RCA paths

- Date: 2026-07-19 JST
- Goal: Create a recoverable backup commit before multi-file Main LAVIE OpenFOAM case work.
- Context: Branch `feat/mecha-autorig`; heavily dirty worktree with unrelated user changes that must be preserved.

## Observed facts

- `git commit --only <four-new-doc-paths>` exited with code 1.
- Git reported each path did not match a file known to Git.
- All four files exist locally and are shown as untracked (`??`).
- No commit or push occurred; no existing staged or working-tree change was altered.

## RCA (5 Whys)

1. The backup commit failed because the specified documents were not known to Git.
2. They were not known because they were newly created and untracked.
3. `git commit --only` limits commit content but does not add untracked paths.
4. The procedure skipped the explicit `git add -- <exact-paths>` step.
5. The safety focus on avoiding unrelated staged changes omitted the separate tracking prerequisite.

## Decision rule

IF a path is untracked and must be included in a path-limited commit, THEN first run `git add -- <exact-paths>` and then `git commit --only <exact-paths>`, BECAUSE `--only` does not track new files.

## Countermeasure plan

1. Add only the five exact incident-report paths with `git add --`.
2. Verify the index for those paths only.
3. Commit with `git commit --only` and the same exact paths.
4. Verify unrelated staged paths remain staged and absent from the new commit.
5. Push branch `feat/mecha-autorig` to `origin`.

## Verification

- Pass: commit contains exactly the five RCA files; remote push succeeds; unrelated dirty/staged paths remain unchanged.
- Fail: any unrelated path appears in the commit, push fails, or index state changes unexpectedly.

## Recovery / rollback

- If the limited commit fails again, unstage only the five exact RCA paths and leave all other index state untouched.

## Scope limits

- This backup commit protects the task documentation; the forthcoming remote case is protected separately by using a new disposable directory.

## Web knowledge decision

- External search is unnecessary because Git's local status and error message fully identify the procedural mistake.

## Next experiment

- Run the exact-path add, verify, limited commit, and push sequence.

## Provenance

- Local Git output, 2026-07-19 JST.
