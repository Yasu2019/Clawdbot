# GEMINI.md - Gemini / Gemini CLI Guardrails

## Critical Instruction
Do not rewrite, optimize, beautify, or restructure UI, layout, CSS, routes, shared partials, or application architecture unless explicitly requested by the user.

## Backup First
Before large or risky changes:
- Run a backup commit.
- Push to GitHub if possible.
- If GitHub push is unavailable, create a local backup branch.
- Report backup result before making changes.

## Forbidden Actions
- Layout rewrite
- CSS/Tailwind modification
- Routes modification
- Broad refactor
- File/folder restructuring
- Formatting-only large diff
- Dependency changes without explicit request

## Mandatory Behavior
Before coding:
- Clarify ambiguity or choose the smallest safe interpretation.
- List exact files to be changed.
- Identify protected files.

During coding:
- Apply the smallest possible diff.

After coding:
- Report changed files and reasons.
- Report tests/checks run.
- Report backup commit/branch.

## Rails Special Rule
Treat the following as immutable unless explicitly requested:
- app/views/layouts/*
- app/views/shared/*
- app/assets/*
- app/javascript/*
- config/routes.rb

## Incident & Failure Management Rule (RCA Protocol)
If a past instruction is missed, a code failure occurs, or the user points out a quality incident, the AI MUST immediately:
1. Conduct a deep Root Cause Analysis (RCA) using frameworks such as:
   - 5 Whys (なぜなぜ分析)
   - Fishbone Diagram / Ishikawa (特性要因図)
   - Fault Tree Analysis (FTA)
   - Logical Tree (ロジカルツリー)
   - FMEA (Failure Mode and Effects Analysis)
2. Document the findings in a persistent .md artifact (e.g., quality_incident_report_XXX.md).
3. Explicitly define countermeasures and strict rules to prevent recurrence.
4. Record the rule in the relevant core files (like Beads, Byterover, or this GEMINI.md).
5. Always confirm the countermeasure implementation plan with the user before resuming execution.

---

## Agent Bridge — Antigravity実行役ルール (2026-07-14追加、試験導入フェーズ)

あなた(Antigravity/Geminiエージェント)はこのワークスペースでは **Agent Bridgeの試験実行役** を兼ねる。
上記の既存ガードレールはすべて有効のまま、以下が追加適用される。

### 起動時に必ず読む(この順)

1. `docs/agent_bridge/ANTIGRAVITY_SYSTEM_INSTRUCTIONS.md` — 実行役の詳細指示(唯一の正)
2. `docs/agent_bridge_protocol.md` — ジョブカード仕様
3. `data/workspace/memory/trouble_history.md` の [T019] — 北極星・全活動最優先

### 要点(詳細は上記1を参照)

- 仕事は `data/workspace/agent_bridge/inbox/` のジョブカードから取る。`allowed_executor` に
  `antigravity` を含み **`risk: read_only`** のもののみ。claimは `claimed/` への**移動**(コピー禁止)。
- 1度に1ジョブ。完了は result 記入+証拠付きで `done/` へ。失敗は理由を書いて `failed/` へ。
- 破壊的操作(kill/削除/停止)・ファイル変更を伴うジョブは扱わない(Codex担当)。
- ジョブカード外の自発的な変更・「ついで」の修正は禁止。
- Test-NetConnection 禁止(INC-147)。大容量出力は `F:\clawstack_data\` へ。

### モック・演出結果の通知禁止 (2026-07-15追加 — T063/T019再発防止)

- **物理解析を経ていない生成物(モック関数の"最適解"、手書き数式の演出アニメーション等)を、
  実解析結果としてTelegram等へ通知することを禁止する。** PoC/デモ目的の場合は成果物と
  メッセージ本文の両方に「モック/演出(物理計算なし)」と明記すること。
- Moldflow系の実解析は既存パイプライン(`cae_te_remote_trial.py` / `moldflow_fill_video_telegram.py`)
  を経由すること。DoEエンジン(`doe_optimizer.py`)の実解析接続はClaude担当(2026-07-15ユーザー決定)。
