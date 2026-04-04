# OpenClaw Obsidian Guide

## Purpose

This vault is the shared working area between Obsidian and OpenClaw.

The goal is:

- keep plans and walkthroughs easy to read in Obsidian
- make project notes searchable from scripts
- provide a safe inbox for AI-generated drafts
- provide a safe landing area for promoted Open Notebook summaries
- preserve a path for future RAG or Learning integration

## Recommended Structure

- `task.md`
  Current active task list.
- `implementation_plan_*.md`
  Medium to large implementation plans.
- `walkthrough.md`
  Human-readable operational steps.
- `AI_Inbox.md`
  AI append-only draft area.
- `05_Research_Summaries/`
  Durable promoted research notes.
- `OpenClaw_Reports/`
  Generated reports that should stay easy to find.
- `.openclaw/`
  Generated index and status files.

## Safe Operating Rules

- Prefer read-only use of existing notes.
- Let OpenClaw write to `AI_Inbox.md` first.
- Move accepted content from `AI_Inbox.md` into permanent notes manually.
- Do not use the whole vault as a blind ingestion source.
- Keep operational notes in Markdown, not PDFs, when possible.
- Use Open Notebook as the exploratory reading room, then promote only useful summaries into this vault.

## Search / Index

Build index:

```powershell
python data\workspace\obsidian_vault_manager.py build-index
```

Start auto-index watchdog:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_obsidian_vault_watchdog.ps1
```

Search notes:

```powershell
python data\workspace\obsidian_vault_manager.py search "email rag ingest"
```

Project-context lookup:

```powershell
python data\workspace\obsidian_vault_manager.py project-context "gmail ingest watchdog"
```

Show summary:

```powershell
python data\workspace\obsidian_vault_manager.py summary
```

Append to AI inbox:

```powershell
python data\workspace\obsidian_vault_manager.py add-inbox --title "Draft" --body "..." --tags ai_inbox draft
```

Promote an Open Notebook summary into Obsidian:

```powershell
python data\workspace\open_notebook_obsidian_bridge.py --title "Notebook Summary" --source-type pdf --source-title "Example Source" --body "Key findings..." --tags open_notebook draft --write-target inbox
```

Generate customer complaint note:

```powershell
python data\workspace\obsidian_vault_manager.py complaint-report "2026年1月から今日までの顧客からのクレーム内容を教えて" --limit 10 --write-note
```

## Future Expansion

- Add periodic indexing via watchdog or scheduled workflow
- Ingest selected notes into Learning memory or Qdrant
- Add note templates for incident, decision, and implementation records
- Add filtered search by tag, owner, and date
- Route OpenClaw project questions through `project-context` first
- Generate complaint or email summary notes into `OpenClaw_Reports/`
- Promote reviewed Open Notebook summaries into `05_Research_Summaries/`
