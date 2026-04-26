# Obsidian + Open Notebook Workflow

## Purpose

Use Open Notebook as the local AI reading room for PDFs, web pages, audio, and video transcripts.
Use Obsidian as the durable project knowledge base.
Use OpenClaw and Qdrant only for selected notes that should become operational context.

## Role Split

- Open Notebook
  Fast ingestion, summarization, comparison, and exploratory reading.
- Obsidian
  Human-readable project notes, decisions, SOPs, research summaries, and long-term context.
- OpenClaw / Qdrant
  Execution, searchable operational context, and RAG for selected promoted notes.

## Recommended Flow

1. Ingest a source into Open Notebook.
2. Use Open Notebook to summarize or compare the source.
3. Promote only the useful result into Obsidian.
4. Keep exploratory or disposable output in Open Notebook.
5. Promote only stable Markdown notes into OpenClaw project context or Qdrant.

## What Should Move To Obsidian

- Decisions that affect implementation or operations
- Stable research summaries
- SOP updates
- Project plans
- Lessons learned
- Reusable prompts or workflows

## What Should Stay In Open Notebook

- One-off exploratory analysis
- Raw ingestion experiments
- Temporary comparisons
- Large source collections that do not need long-term retention

## Promotion Targets Inside The Vault

- `AI_Inbox.md`
  Safe default write target for AI-generated drafts.
- `05_Research_Summaries/`
  Durable research summaries after human review.
- `03_Projects/`
  Project-specific promoted notes.
- `OpenClaw_Reports/`
  Generated reports that should remain easy to find.

## Standard Commands

Create a draft note from an Open Notebook result:

```powershell
python data\workspace\open_notebook_obsidian_bridge.py `
  --title "Notebook Summary" `
  --source-type pdf `
  --source-title "Example Source" `
  --source-url "https://example.com" `
  --body "Key findings..." `
  --tags open_notebook promoted draft `
  --write-target inbox
```

Promote to a durable research summary:

```powershell
python data\workspace\open_notebook_obsidian_bridge.py `
  --title "Notebook Summary" `
  --source-type web `
  --source-title "Example Source" `
  --body "Key findings..." `
  --tags open_notebook research_summary `
  --write-target research
```

Refresh the shared vault index after promotion:

```powershell
python data\workspace\obsidian_vault_manager.py build-index
```

## Operating Rules

- Do not treat the whole Open Notebook corpus as permanent knowledge.
- Prefer promoting concise Markdown summaries, not raw dumps.
- Default AI writes go to `AI_Inbox.md`.
- Human-reviewed notes should be moved out of `AI_Inbox.md`.
- Only stable promoted notes should be considered for RAG or long-term OpenClaw context.
