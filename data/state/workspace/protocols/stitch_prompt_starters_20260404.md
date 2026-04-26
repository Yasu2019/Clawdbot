# Stitch Prompt Starters (2026-04-04)

このメモは、Google Stitch へそのまま貼り付けて使える初稿用プロンプト集です。  
前提は「見た目の初稿だけを Stitch に任せ、業務ロジックと状態判定は Codex が実装する」です。

## 1. Portal TOP

Create a Japanese desktop-first internal portal homepage for an AI engineering workstation. Use a premium but practical card dashboard style. Prioritize: category grouping, compact card density on wide monitors, clear status badges, and a strong hero summary. Include cards for AI chat, n8n, Paperless NGX, Learning Memory, Email Search, Ingestion/RAG Control Center, Note Pro, and Stitch UI Evaluation. The output should be a visual shell only. Do not invent backend logic, dangerous actions, or database flows.

## 2. Ingestion / RAG Control Center

Design a Japanese operations dashboard for Gmail ingestion, Paperless document ingest, Learning sync, and RAG observability. Show an overall health banner, compact metric cards, aging indicators, and quick links to detailed tools. This should look operational and trustworthy, with emphasis on degraded states and what to open next. Visual design only. Assume Codex will wire JSON and API logic later.

## 3. Note Pro

Create a Japanese writing workspace for drafting articles from recommended AI and OSS news. Layout should include a left recommendation rail, a central editor, and a right-side assistance panel for structure and prompts. Make it editorial and focused, not generic SaaS. Keep the design suitable for a local AI tool. UI only, no fake backend implementation.

## 4. Open Notebook -> Obsidian

Design a Japanese workflow hub that explains how Open Notebook summaries are promoted into Obsidian safely. Show stages, guardrails, recommended destinations like AI_Inbox, and a simple review-first flow. The page should feel instructional and reliable. No backend logic; this is a UI concept that Codex will later connect to scripts.
