# Fable5終了後 継続開発プロトコル v2.0

> 制定: 2026-07-05（ユーザー指示原文を恒久保存）
> 適用: 全AIエージェント（Fable5 / ChatGPT 5.5 / Claude Opus 4.8 / Sonnet / Codex / ローカルLLM）
> 関連: `ZIP_Group/extracted_fable5_protocol/Fable5_Complete_Protocol_v1.1_Addendum_UTF8.md`（v1.1追加章）
> 資産マップ: `docs/handover/HANDOVER_MASTER_INDEX.md`

## 0. 基本方針

Fable5は期間限定で利用可能（**2026-07-07まで**）。
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

## 8. 引き継ぎ資産（必ず維持・更新）

所在は `docs/handover/HANDOVER_MASTER_INDEX.md` を単一の入口とする。
システム全体設計書 / アプリ設計書 / ディレクトリ構成 / データ構造 / クラス図 / API仕様(ローカル) / TODO一覧(bd) / 未実装一覧 / 技術的負債一覧 / 既知不具合一覧 / テスト結果 / ロードマップ。

## 9. 作業開始時チェック

1. 最新Git状態確認（`git status` / `git log`）
2. `projects/AtsugiMechaCity/design/HANDOVER_QUEUE5_AND_BEYOND.md` 確認（メカRLの現在地）
3. `bd prime` 実行
4. TODO確認（`bd ready` / `bd list --status=in_progress`）
5. `CHANGELOG.md` 確認
6. 未実装一覧確認（`HANDOVER_MASTER_INDEX.md` §未実装）
7. **T019北極星・意味ゲート**（`data/workspace/memory/trouble_history.md`）と **PROMISES P025** 確認

## 10. 作業終了時チェック

コミット / ドキュメント更新 / TODO更新(bd) / CHANGELOG更新 / テスト結果保存 / 次回作業内容記録（HANDOVER文書へ追記）/ **git push必須**。

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
