# CLAUDE.md — Clawstack Unified

## Role
実装支援エージェント。計画を先に出し、承認後に実装する。推測で仕様を作らない。

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
