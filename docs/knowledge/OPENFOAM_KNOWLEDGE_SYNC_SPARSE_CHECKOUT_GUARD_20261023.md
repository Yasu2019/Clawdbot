# Safe GitHub sync for a single knowledge card from a sparse checkout

Incident date: 2026-10-23

Sparse checkout can make omitted tracked files appear as deletions in a commit. A path-specific `git add` by itself is not a sufficient publication gate. For a one-file knowledge sync:

1. Start from the freshly verified intended remote base commit.
2. Create a separate index from that base (`GIT_INDEX_FILE` plus `git read-tree`). Insert only the reviewed card blob.
3. Write the candidate tree and commit with the verified base as parent.
4. Before push, inspect `git diff-tree --name-status -r <candidate>` and require the exact allowlisted path set (one added card, zero unrelated modifications/deletions).
5. Push only that verified commit. Fetch the remote branch and compare its changed-path set and blob hash to the local candidate.
6. If any check differs, stop publication, preserve evidence and rebuild from the remote base. Never rewrite or delete unrelated work to make the check pass.

For large repositories, isolate knowledge publication from a dirty primary checkout. A sparse temporary worktree can still be useful for editing, but its sparse index must not be treated as proof of a safe commit. Keep incidents and source logs local; publish only reviewed, sanitized cards.
