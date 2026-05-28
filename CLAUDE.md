# CLAUDE.md — Clawstack Unified

## Role
実装支援エージェント。計画を先に出し、承認後に実装する。推測で仕様を作らない。

## Quality Analysis Protocol（全タスク必須・スキップ禁止）
ユーザーの全指示に対して、実装・回答の前に以下の品質分析を実施すること:
1. **QC工程表(PMP)** — 作業ステップと管理ポイントを列挙
2. **FMEA** — 各ステップの潜在的故障モード・影響度・対策
3. **FTA / なぜなぜ分析 / Fishbone** — 根本原因の事前想定と予防策
→ 詳細ルール: `docs/quality_analysis_protocol.md`

## Must
- 実装前に必ず Plan を出す（ファイル・関数・影響範囲・リスクを含む）
- 変更対象ファイルを明示し、変更範囲を最小化する
- 不明点は推測ではなく仮定として明記する
- 完了時に「変更ファイル / 変更内容 / 未解決事項 / 次回推奨」を要約する
- 作業前に `data/workspace/memory/trouble_history.md` と `data/workspace/PROMISES.md` を確認する
- **新規コードでポートを使う場合は必ず `docker-compose.yml` の実ポートを確認してから書く**（推測・慣例での記載禁止 → T008）

## Avoid
- 関係ないファイルの横断探索
- 指示されていないリファクタ・コメント追加・型注釈追加
- 1セッションで設計・実装・レビューをすべて完結させようとする
- CLAUDE.md に思想・背景・運用細則を追記して肥大化させる
- **UIレイアウトの無断変更（→ PROMISES.md P022）**: `iatf_system/app/views/` および `data/workspace/apps/` は必ずPlan提示・ユーザー承認後のみ変更可

## Critical Constraints
- Docker build は **必ずキャッシュ使用**。`--no-cache` は事前説明なしに禁止
- `clawstack_v2/data` は Junction Point。削除前にジャンクション確認必須
- OpenClaw Gateway token: `yasu-fresh-token-2026-02-01`

## Model Routing (参考)
- 軽タスク（確認/要約/定型）→ `local_fast`（qwen3:8b / 無料）
- 通常タスク（修正/デバッグ/編集）→ `google/gemini-2.5-flash`
- 重タスク（設計/根本原因/方針）→ Plan Mode 先行 + `google/gemini-2.5-flash`
- 実装専用（差分生成/一括置換）→ `codex`（qwen3:8b / 無料）

## Key Paths
- LiteLLM config: `data/state/litellm_config.yaml`
- Model router: `data/workspace/model_router.py`
- Session protocol: `docs/token_saving_session_protocol.md`
- Trouble log: `data/workspace/memory/trouble_history.md`

---
# Added by AI Surgical Guardrails v1

# CLAUDE.md - Claude Code Guardrails

## Core Principles
- Think Before Coding
- Simplicity First
- Surgical Changes
- Goal-Driven Execution
- Backup Before Large Change

## Hard Constraints
- No broad refactor without explicit approval.
- No layout, CSS, route, shared partial, or architecture change without explicit approval.
- No large formatting-only changes.
- No hidden file moves or dependency changes.

## Backup Rule
Before multi-file edits, refactors, UI/layout changes, or risky changes:
1. Commit current state.
2. Push backup to GitHub if possible.
3. If push fails, create local backup branch.
4. Report backup result.

## Editing Policy
Only touch code required to satisfy the requested goal.

## Diff Quality
Keep diffs minimal, readable, and reviewable.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
