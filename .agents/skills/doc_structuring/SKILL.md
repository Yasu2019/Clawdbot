---
name: doc_structuring
description: "Use when turning PDF text, OCR text, meeting notes, or raw memos into structured summaries, action items, risks, and report-ready output in this project. Prefer extracting only the needed facts, unresolved points, and follow-up actions rather than rewriting the whole source."
---

# Doc Structuring Skill

Use this skill for document digestion, memo normalization, meeting note cleanup, and turning noisy source text into structured output.

## Workflow

1. Confirm the input type:
   - PDF text
   - OCR text
   - raw notes
   - transcript
2. Keep only the minimum facts needed for the user's output:
   - key points
   - action items
   - risks
   - unresolved questions
3. Do not restate the whole document if the user needs a working summary.
4. If the text is noisy or partially broken, separate:
   - confirmed facts
   - likely meaning
   - unknown / unreadable parts
5. When the output will feed another tool or workflow, prefer stable headings and short bullet-ready structure.

## Rules

- Preserve uncertainty instead of over-normalizing ambiguous OCR text.
- Prefer compact structured summaries over long paraphrases.
- Make follow-up actions explicit.
- For high-stakes outputs, keep source-backed facts and open questions separate.

## Read first when relevant

- `data/workspace/open_notebook_obsidian_bridge.py`
- `data/state/workspace/protocols/context_budget_protocol_20260404.md`

