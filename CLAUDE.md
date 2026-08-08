# CLAUDE.md — Clawstack Unified

## 🎯 北極星・全活動最優先（T019 / P025 — 作業前必読）

**最終目標:** ユーザーのプレス部品3D → Moldflow級充填 + Cetol6Sigma級公差 + OpenRadioss曲げ/打ち抜き → **順送金型開発**。  
**禁止:** 物理と無関係なループ・通知（例: `resin_flow` 薄管icoFoam + 2D ParaView |U|）。  
**必読:** `data/workspace/memory/trouble_history.md` **[T019]** · `docs/cae_north_star_and_meaning_gate_protocol.md` · PROMISES **P025** · `bd remember --key cae-north-star-t019`

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
- 作業前に `data/workspace/memory/trouble_history.md`（**[T019]最優先**）と `data/workspace/PROMISES.md`（**P025**）を確認する
- **新規コードでポートを使う場合は必ず `docker-compose.yml` の実ポートを確認してから書く**（推測・慣例での記載禁止 → T008）

## Avoid
- 関係ないファイルの横断探索
- 指示されていないリファクタ・コメント追加・型注釈追加
- 1セッションで設計・実装・レビューをすべて完結させようとする
- CLAUDE.md に思想・背景・運用細則を追記して肥大化させる
- **UIレイアウトの無断変更（→ PROMISES.md P022）**: `iatf_system/app/views/` および `data/workspace/apps/` は必ずPlan提示・ユーザー承認後のみ変更可

## Critical Constraints
- **🔍 着手前に蓄積知識を検索する（グローバルルール / 2026-08-08 ユーザー指示）**: 「trouble_history.md を確認」だけでは実際には読まれない。**コマンド実行を作業手順に組み込む**。
  - `python scripts/search_docs.py "<これから触る対象・症状>"` を実行し、ヒットした過去知見を要約してから着手する（意味検索・`clawstack_docs`）
  - 日本語キーワードで引く場合: `scripts/build_ja_fts_index.py` が作る `universal_growth_fts_ja.db`（`knowhow_ja` / `pdftext_ja` / `material_ja`、trigramは**3文字以上**）
  - **実例（このルールが生まれた理由）**: 2026-08-08、T067「歩行RLの best travel は歩行距離ではなく**転倒滑走距離**だった」を読まずに `walk_20260720_cycle03_travel1.63.pt` を resume 元に選び、滑走方策を継承したまま4サイクル空転させた。検索していれば初手で回避できた
- **📝 文字化け防止は絶対（グローバルルール / 2026-08-08 ユーザー指示）**: MDファイル・DB・ログへの**書き込みと読み込みは必ず encoding を明示**する。
  - Python: `open(..., encoding="utf-8")` を必ず指定（既定はcp932）。書き込み後は読み戻して `U+FFFD` と化け記号(`縺`/`繧`/`繝`)が無いことを確認する
  - PowerShell: `Get-Content`/`Set-Content`/`Add-Content` の既定はANSI(cp932)。日本語を扱うなら `-Encoding utf8` 必須。`Out-File` も同様
  - SQLite/Qdrant: 投入前に `str` が正しくデコード済みか確認し、投入後に1件読み戻して往復検証する
  - **表示の化けと実ファイルの破損を混同しない**: コンソールが化けても実体は正常なことが多い。`open(f,"rb").read().decode("utf-8")` が通るかで判定し、表示だけを根拠にファイルを"修正"しない
- **🤖 3Dメカ目視確認は絶対（グローバルルール / 2026-07-24 ユーザー指示）**: RL歩行・動作学習・リギング等、3Dメカロボットの学習/評価/レンダ結果を報告・合格判定する前に、**必ずフレーム画像を目視**し、胴体-腕-脚の連結・姿勢・接地に異常が無いことを自分の目で確認する。survival等の**数値だけで合格としない**（立ち止まりが高survivalに化ける/腕分離等の物理破綻は数値に出ない）。レンダは `render_walk_rsl.py`(v2) 等でPNGを出し `Read` で確認。徹底管理: Beads(`bd remember`)・Byterover queue・Obsidian Vault(`FailureKnowledge/`)・auto-memory に記録済み。
- **大容量データはF:ドライブへ**: データセット・学習成果物・動画・アーカイブ等(目安100MB超)は `F:\clawstack_data\` 配下に保存する。D:は容量逼迫のためコード・設定・小サイズ状態ファイルのみ(2026-07-12 ユーザー指示)
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
