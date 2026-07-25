# Fable5終了後 継続開発プロトコル v2.1

> 制定: 2026-07-05（ユーザー指示原文を恒久保存）/ 改訂: 2026-07-09 v2.1（§7.1衛星配布・§7.2五層記録・§9/§10増補 = T050〜T054教訓の恒久化）
> 適用: 全AIエージェント（Fable5 / ChatGPT 5.5 / Claude Opus 4.8 / Sonnet / Codex / ローカルLLM）
> 関連: `ZIP_Group/extracted_fable5_protocol/Fable5_Complete_Protocol_v1.1_Addendum_UTF8.md`（v1.1追加章）
> 資産マップ: `docs/handover/HANDOVER_MASTER_INDEX.md`（単一の入口）
> 直近セッション差分: `docs/handover/FABLE5_FINAL_SESSION_HANDOVER_20260707.md`（未完アクション・bd起票リスト）

## 0. 基本方針

Fable5は期間限定で利用可能（**2026-07-07まで**）→ **本フェーズは発効済み（2026-07-08〜）**。以降Fable5セッションが臨時に得られた場合も§3の役割（設計・品質・引き継ぎ最優先）で振る舞う。
本プロジェクトの目的はFable5に依存することではない。
Fable5終了後も ChatGPT 5.5 / Claude Opus 4.8 / Codex / Sonnet / ローカルLLM のみで長期間継続開発できる開発体制を完成させる。
Fable5は「最終設計者・品質改善者・引き継ぎ責任者」として振る舞う。

## 1. 最重要目標

7月7日以降、**Fable5が存在しなくても開発速度が落ちないこと**。
新機能追加よりも 設計整理 / ドキュメント整備 / 共通化 / 引き継ぎ を優先する。

## 2. 開発対象

1. 3Dロボット機械学習アプリ（完全ローカル・API非依存）
2. CETOL 6σ風 公差解析アプリ
3. DXF→3Dモデル生成アプリ
4. OpenRadiossせん断加工解析アプリ
5. Moldflow風簡易解析アプリ

必要に応じて Unity / ML-Agents / MuJoCo(Genesis) / Blender / OpenUSD 連携も整理する。

## 3. Fable5期間中の役割

アーキテクチャ改善 / リファクタリング / 共通ライブラリ化 / 品質改善 / テスト追加 / ドキュメント作成 / 引き継ぎ資料作成 を最優先。

## 4. ChatGPT 5.5の担当

新機能追加 / アルゴリズム改善 / UI改善 / バグ修正 / 技術調査 / ドキュメント更新。
設計変更時は既存設計との整合性を確認すること。

## 5. Claude Opus 4.8の担当

大規模設計 / リファクタリング / コードレビュー / 品質向上 / 技術的負債削減。

## 6. Codexの担当

実装 / テスト / 修正 / 自動化 / CI支援。

## 7. 共通ルール（全AI遵守）

- UTF-8固定（cp932絵文字ログエラー回避: `PYTHONIOENCODING=utf-8`）
- 日本語コメント / Windows対応
- README更新 / requirements.txt更新 / CHANGELOG更新（ルート `CHANGELOG.md`）
- TODO更新（**単一情報源は bd** — `bd create`/`bd close`。Markdown TODOリスト複製禁止 = CLAUDE.mdルール）
- テストコード追加 / ログ出力 / 例外処理
- ゲート許容値を勝手に緩めない（FMEA#2 RPN432）/ ゲート判定へのLLM使用禁止（決定論のみ）

### 7.1 衛星ノードへのコード配布ルール（T050/T051の恒久化）

- `cae_te_engine.py` と `cae_self_growth_gates.py` は**必ずペアで配布**し、双方SHA256照合+`py_compile`確認（片方のみの配布は版数不整合→偽ERROR = T051）
- 配布前にorchestrator/watchdogを**全停止**（ワーカーは単線、syncジョブ中は`/jobs`ブロック）。watchdogは二重起動を検知しない（pid複数表示が兆候）
- ダウンロードは `Invoke-WebRequest` を使う（certutilはサービス文脈でWinINet起因の無言失敗）
- `docker run` をsubprocess timeoutで管理する場合はコンテナ内 `timeout -k` 併用（クライアントkillのみではコンテナ孤児化 = T050）
- 手順書: `docs/handover/T051_GATES_VERSION_MISMATCH_20260706.md` / 配布スクリプト例: `k10_t051_deploy_all_in_one.ps1`

### 7.2 障害・教訓の五層記録（省略禁止）

新規障害は解決時に以下5層へ同時記録する。1層でも欠けると次AIが検索で見落とす（4ソース照合=§9-3の前提）。

| 層 | 格納先 | 粒度 |
|---|---|---|
| 過去トラDB | `data/workspace/memory/trouble_history.md` | T番号採番+表1行（事象/対策/教訓） |
| 手順書・個票 | `docs/handover/T*_*.md` / ルート `quality_incident_report_*.md` | 再現手順・罠・残作業まで |
| ByteRover | `.brv/context-tree/<アプリ>/` | AI検索用コンテキスト |
| Obsidian | PCログ=`data/state/Obsidian Vault/60_PC_Logs/` / 知識系=`data/workspace/obsidian_vault/` | セッションログ |
| Beads | `bd create` 新規 / 既存issueへ追記 | タスク・ステータス |

**参照実装（2026-07-06〜07の実記録・全5層記録済）:** trouble_history=[T051]〜[T054] / 手順書=`T051_GATES_VERSION_MISMATCH_20260706.md` / brv=`dxf2step/dxf2step-s1-false-fail-6layer-fix-5yk-20260706.md`・`cae/t051-red-lavie-pair-deploy-traps-20260706.md` / Obsidian 60_PC_Logs=`DXF2STEP_5yk_S1_6layer_false_fail_fix_20260706.md`・`T051_T052_fleet_recovery_and_deploy_20260706.md` / bd=更新 `tq1`/`5yk`/`ip4`・新規 `9tgj`/`7c62`

## 8. 引き継ぎ資産（必ず維持・更新）

所在は `docs/handover/HANDOVER_MASTER_INDEX.md` を単一の入口とする。
システム全体設計書 / アプリ設計書 / ディレクトリ構成 / データ構造 / クラス図 / API仕様(ローカル) / TODO一覧(bd) / 未実装一覧 / 技術的負債一覧 / 既知不具合一覧 / テスト結果 / ロードマップ。

## 9. 作業開始時チェック

1. 最新Git状態確認（`git status` / `git log`）
2. `docs/handover/FABLE5_FINAL_SESSION_HANDOVER_20260707.md` の未完アクション確認（G3復旧・DOE誘導など）
3. **4ソース事前照合**: 対象アプリの Beads(`bd list`/`bd memories`) / ByteRover(`.brv/context-tree/`) / Obsidian / 過去トラDB を照合（`HANDOVER_MASTER_INDEX.md` §7が全アプリ照合結果。brvルール`atsugi-mecha-joint-gate-preflight`の全アプリ版）
4. `projects/AtsugiMechaCity/design/HANDOVER_QUEUE5_AND_BEYOND.md` 確認（メカRLの現在地）
5. `bd prime` 実行
6. TODO確認（`bd ready` / `bd list --status=in_progress`）
7. `CHANGELOG.md` 確認
8. 未実装一覧確認（`HANDOVER_MASTER_INDEX.md` §未実装）
9. **T019北極星・意味ゲート**（`data/workspace/memory/trouble_history.md`）と **PROMISES P025** 確認
10. **死活再チェック結果確認**（`data/workspace/dead_project_recheck_status.json` — checked_atが26h超なら チェッカー自身が死亡 → `docs/dead_project_recheck_protocol.md` に従い手動実行。2026-07-07制定）
11. **成長ループ監査結果確認**（`data/workspace/growth_loop_audit_status.json` — FAKE_GROWTHがあれば48h以内に是正orループ停止。成長ループ新設時は `growth_loop_manifest.json` 登録必須 = `docs/growth_loop_quality_protocol.md`。**ゲート判定へのLLM使用禁止**。2026-07-07制定）

## 10. 作業終了時チェック

コミット / ドキュメント更新 / TODO更新(bd) / CHANGELOG更新 / テスト結果保存 / 次回作業内容記録（HANDOVER文書へ追記）/ **git push必須**。
新規障害が発生した場合は **T番号採番+§7.2の五層記録** を完了させてからセッションを終える（省略禁止）。bd実行不可の環境で作業した場合は「bd起票要」を差分文書に明記し、次セッション冒頭で起票する。

## 11. 品質基準

すべての変更は ビルド可能 / テスト可能 / 再開可能 / 保守可能 であること。
既存の品質プロトコル（`docs/quality_analysis_protocol.md`・QC工程表/FMEA/FTA）と意味ゲート（T019/P025）を併用する。

## 12. 最終ゴール

最終成果物はコードだけではない。以下を同時に完成させる:
長期運用できる設計 / 他AIが理解できるドキュメント / 引き継ぎ資料 / テスト資産 / 運用手順 / 障害復旧手順 / 開発ロードマップ。

**Fable5終了後も、ChatGPT 5.5・Claude Opus 4.8・Codex・Sonnet・ローカルLLMだけで継続開発できる状態の完成が本プロジェクトの最終目標。**

---

## 付録: v1.1追加章（Addendum）要点

- 100〜200ページ相当の設計・運用ドキュメントを**段階的に**整備（一括生成禁止・実態と乖離させない）
- アーキテクチャ: フォルダ構成図 / データフロー図 / クラス図 / コンポーネント構成図 / 依存関係整理
- AIエージェント運用: 役割分担・引き継ぎプロトコル・共通プロンプト資産
- 品質・運用: テスト戦略 / CI/CD / 障害復旧フロー / ログ管理 / チェックポイント管理 / バージョン管理方針
