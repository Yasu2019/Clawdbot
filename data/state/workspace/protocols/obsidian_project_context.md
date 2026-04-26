# Obsidian Project Context Protocol

## Purpose

Use the shared Obsidian vault as the first local source for active plans, task status, walkthroughs, and project-specific operating notes.

Vault path:
- `/home/node/clawd/obsidian_vault/Clawstack_Project`

## Preferred Source Order

1. `task.md`
2. `implementation_plan_*.md`
3. `walkthrough.md`
4. `PORTAL_APPS.md`
5. `AI_Inbox.md`
6. General vault search results

## Standard Commands

Focused project lookup:

```bash
python3 /home/node/clawd/obsidian_vault_manager.py project-context "<user request>" --limit 5
```

General note search:

```bash
python3 /home/node/clawd/obsidian_vault_manager.py search "<user request>" --limit 5
```

Refresh index after vault changes:

```bash
python3 /home/node/clawd/obsidian_vault_manager.py build-index
```

Windows watchdog launcher:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\start_obsidian_vault_watchdog.ps1
```

Append a draft safely:

```bash
python3 /home/node/clawd/obsidian_vault_manager.py add-inbox --title "Draft" --body "..." --tags ai_inbox draft
```

Promote an Open Notebook summary into the vault:

```bash
python3 /home/node/clawd/open_notebook_obsidian_bridge.py --title "Notebook Summary" --source-type pdf --source-title "Example Source" --body "Key findings..." --tags open_notebook draft --write-target inbox
```

Generate a customer complaint note from the local email DB:

```bash
python3 /home/node/clawd/obsidian_vault_manager.py complaint-report "2026年1月から今日までの顧客からのクレーム内容を教えて" --limit 10 --write-note
```

## Operating Rules

- Treat Obsidian as local evidence, not just background notes.
- Prefer Markdown notes over stale chat memory when both exist.
- Default AI writes go to `AI_Inbox.md`.
- Do not overwrite permanent notes automatically unless the human explicitly asks.
- If search results are weak, rebuild the index once before concluding no relevant note exists.
- For ongoing local use, prefer the watchdog so Obsidian edits are picked up automatically.
- For complaint or email-originated lists, prefer generating a fresh note from the local email DB instead of trusting stale vault text alone.
- Treat Open Notebook as the staging area for ingestion and exploratory summaries.
- Promote only stable Markdown summaries into Obsidian.
- Use `AI_Inbox.md` as the default landing area for Open Notebook-derived drafts unless the user explicitly wants a durable research note.
