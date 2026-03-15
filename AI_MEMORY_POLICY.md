# ByteRover Memory Policy

Before complex tasks:
1. Query ByteRover for relevant prior decisions or architecture notes.
2. Prefer specific questions tied to files, services, or workflows.

After important tasks:
1. Curate durable knowledge into ByteRover.
2. Store decisions, failure modes, runbook-worthy fixes, and environment facts.
3. Do not store raw secrets, tokens, passwords, or private personal content.

Recommended commands:

```powershell
brv query "How is <topic> implemented in this workspace?"
brv curate "Decision summary with file references and why it matters"
```

Project-specific rules:
- Use ByteRover as long-term memory, not as a dump for every transient step.
- Keep `MEMORY.md` and daily notes for human-facing continuity when needed.
- Prefer host-side ByteRover usage; do not modify Docker services for ByteRover without an approved implementation plan.
