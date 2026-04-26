approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "live"

# Mission
OpenClaw既存環境に Workspace Agents Hub を本番安全設計で統合する。

# Non-negotiable Safety
- Never execute write SQL.
- Never expose secrets.
- Never send external notifications without HITL design gate.
- Never overwrite existing portal cards without backup.
- Detect port conflicts before edits.

# Tasks
1. Inspect repository and compose topology.
2. Place this extension under extensions/workspace_agents.
3. Validate FastAPI service locally.
4. Create patch plan for docker compose override.
5. Add Portal card link safely.
6. Import n8n flow as draft if n8n CLI/API is available; otherwise save instructions.
7. Run smoke tests.
8. Produce REPORT_WORKSPACE_AGENTS.md with:
   - files changed
   - commands run
   - test results
   - unresolved items
   - recommended next actions

# Decision Policy
- If conflict is found: do not force. Create *_candidate files and report.
- If dependency is missing: implement fallback and document it.
- If OpenClaw endpoint differs: discover current endpoint from compose/env/docs.
