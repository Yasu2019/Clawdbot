# AI Agent Safety Policy

Mandatory rules for Claude Code, Codex, OpenClaw, Gemini CLI, VSCode agents, and Antigravity:

1. No destructive edits without explicit approval.
2. Before large modification, create backup or Git commit.
3. Prefer additive files over rewriting existing production files.
4. Always run in dry-run mode first for file moves.
5. Preserve existing Portal cards and Docker services.
6. Use local LLM first when possible; use cloud models only for high-value judgment.
7. If conflicts are detected, stop and write a conflict report.
