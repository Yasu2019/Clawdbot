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
- **🌐 ローカルに知見が無ければ外部を調べる（グローバルルール / 2026-08-10 ユーザー指示）**: 自前の試行錯誤より、公開実装を読む方が速く確実なことがある。
  - `python scripts/research_gate.py "<対象>"` で判定する。**exit 2 なら外部調査を先に行う**（黙って自前実装に走らない）
  - 調べる順: ①**公開実装の設定ファイル**（論文より速い）→ ②WebSearch は「ライブラリ名＋設定キー名」で引く（概念語だけで探さない）→ ③一次情報で裏取り
  - **実例（このルールが生まれた理由）**: 2026-08-10、RL歩行の転倒率100%を数時間デバッグしたが、答えは [unitree_rl_gym G1](https://github.com/unitreerobotics/unitree_rl_gym/blob/main/legged_gym/envs/g1/g1_config.py) に1行で書かれていた（`terminate_after_contacts_on = ["pelvis"]` / `penalize_contacts_on = ["hip","knee"]`）。収集コーパスは humanoid 15件・legged 8件で実質ゼロだった
  - **収集コーパスを過信しない**: 30万件の実体は一意5,591件で、分野も北極星と噛み合っていない
- **🔢 定数を「バグ」と断じる前に検索する（グローバルルール / 2026-08-18 ユーザー指示）**: 正規の基準定数をマジックナンバーと誤認して削除し、有効な成果を無効化・再学習まで走らせた。
  - `python scripts/check_constant.py "<値>"` を実行する。**exit 2 なら名前付き定義あり＝消すな**
  - **一定オフセットは「バグの証拠」ではなく「基準が違う証拠」であることの方が多い**。2つの量の差を根拠にする前に、座標原点・単位・符号が同一かを明示的に確認する
  - **検証は変更した式**以外**の独立した経路で行う**。式を式で検算するのは循環論法。実測・目視など別系統の証拠を取る
  - **仮説が実測で確定するまで、コミット・既存成果の無効化・長時間ジョブの起動をしない**
  - **実例（このルールが生まれた理由）**: 2026-08-18、傾斜板の `zc = -0.92 + ...` の `-0.92` を除去したが、同一リポジトリの2箇所（`FLOOR_TOP` / `FLOOR_Z`）で定義された床天面の基準値だった。ジオメトリ(世界座標)と `terrain_dz`(床面基準)を引き算して出た当然の差を不整合と誤認した。詳細: `trouble_history.md` **[T079w]**
- **🗂 発見は1コマンドで全系統に記録する（グローバルルール / 2026-08-10 ユーザー指示）**: 「複数系統に書く」を努力目標にすると必ず抜ける。
  - `python scripts/record_finding.py --title "..." --what "..." --why "..." --how "..." --evidence "..."`
  - 記録先は **Beads / Obsidian `obsidian_vault/トラブルシューティング/` / auto-memory** の3系統。3/3 成功を確認する
  - **実在しない記録先に書かない**: `FailureKnowledge/` は存在しない（実在は `トラブルシューティング/`）。Byterover はコンテナ未稼働、Turso はメール用のみ。復旧したら `record_finding.py` に追加する
  - graphify は hook が毎回600秒でタイムアウトし `manifest` が更新されない（既知の未解決事項）
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
- **🔬 CAEシミュレーション実行前にt=0（変形前）フレームの目視確認は絶対（グローバルルール / 2026-09-04 ユーザー指示）**: OpenRadioss/OpenFOAM等のCAEモデルを構築したら、長時間ジョブを起動する**前に**、必ずt=0（初期・未変形）フレームを目視し、注目領域（穴・くびれ・接合部等）に**意図したジオメトリ・材料が実際に存在するか**を確認する。Starterの「0 ERROR/0 WARNING」は要素が生成されたことしか保証せず、**意図した場所に材料があることは保証しない**。
  - 破断パターン・変形後の可視化を繰り返しても、**入力（初期ジオメトリ）そのものの目視確認を代替しない**。「出力は入念に検証するが入力は検証しない」という盲点を作らない
  - 複数ソリッドをfuse/boolean結合するメッシュ生成では特に注意（反転法線の重複ソリッドで体積が相殺され、穴埋め用シリンダー等が実際には要素を持たないまま静かに欠落することがある）
  - **実例（このルールが生まれた理由）**: INC-188の丸穴(φ0.56mm)診断で、`add_slug`シリンダーが実際には材料を生成していない(fuse後の反転複製で体積相殺+半径不一致)バグに数週間気づかず、境界条件仮説・エンゲージ時間仮説・GENE1二重発火バグ修正など多数の調査を積み重ねた。ユーザーが動画で「矩形・トリム接触前から穴が開いて見える」と指摘し、初めてt=0を確認して発覚。最初にt=0を見ていれば大部分の調査が不要だった
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


## Moldflow Material Property Database & TCode Extraction Knowledge
- **Location**: `D:\Clawdbot_Docker_20260125\data\workspace\moldflow_bridge\moldflow_materials.db` (SQLite) & Turso Cloud (`clawstack-knowledge`).
- **Catalog**: 8,161 commercial polymer grades normalized in `materials_catalog_normalized.json`.
- **Extraction Protocol**: Do NOT attempt GUI scraping. Solver preflight (`runstudy.exe -c`) generates unencrypted TCode parameters in `~2.out`:
  - `TCode 1313`: Cross-WLF (n, tau*, D1, D2/Tg, D3, A1, A2)
  - `TCode 1004`: 2-domain Tait pvT (13 parameters: b1m-b4m, b1s-b4s, b5-b9)
  - `TCode 4001`: CRIMS shrinkage coefficients (A1-A6)
  - `TCode 1100, 1200, 1602, 1702`: Cp, k, E1, E2, Nu, G12, CTE
- **Remote Host**: Dynabook (`100.98.133.40`), SSH key `C:\Users\yasu\.ssh\moldflow_remote_ed25519`.
