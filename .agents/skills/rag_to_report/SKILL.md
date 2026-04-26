---
name: rag_to_report
description: "Use when converting RAG search results from Paperless, Qdrant, or local knowledge sources into a cited report, answer draft, or evidence summary in this project. Prefer concise, source-backed synthesis and clearly mark remaining unknowns."
---

# RAG to Report Skill

Use this skill when search results exist and the task is to turn them into a usable answer, report draft, or evidence memo.

## Workflow

1. Check what sources are available:
   - Paperless documents
   - Qdrant-backed RAG
   - local status / audit JSON
2. Extract only the evidence needed for the requested output.
3. Group findings into:
   - answer / conclusion
   - supporting evidence
   - missing evidence
   - follow-up questions
4. Keep the output cited and compact.
5. If the retrieved material is weak, say so explicitly instead of smoothing over the gap.

## Rules

- Do not present uncited synthesis as a confirmed fact.
- Prefer a short evidence-backed report over an exhaustive dump.
- Keep open questions visible.
- Use the project's context-budget pattern when the retrieved material is large.

## Read first when relevant

- `data/state/workspace/protocols/context_budget_protocol_20260404.md`
- `data/workspace/rag_search.py`
- `data/workspace/paperless_ingest_audit_summary.md`

