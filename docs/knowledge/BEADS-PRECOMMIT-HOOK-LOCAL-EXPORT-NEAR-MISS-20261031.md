# Beads pre-commit export during a one-card publication

Observed: 2026-10-31, JST. A narrowly staged knowledge-card commit invoked the repository's configured Beads pre-commit hook, which rewrote the local Beads JSONL export in another worktree. That file already had staged changes before the commit. The remote commit tree was read back and contained only the reviewed sanitized card. A read-only canonical-record comparison found the rewritten JSONL semantically matched the staged snapshot; the line ordering/representation changed. No reset, restore, or unrelated commit was made.

Before future knowledge-card commits, check the shared hook path and exact staged file list. After a commit, verify the remote tree contains only the reviewed card and compare protected local stores against their staged snapshot. Preserve staged work if a hook rewrites a file. This card excludes raw issue contents, credentials, account names and machine addresses.
