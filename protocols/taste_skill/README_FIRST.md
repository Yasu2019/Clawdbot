# Taste Skill 本気版 ZIP（業務UI向け）

この ZIP は、AI が作る UI の「似たり寄ったり化（slop）」を抑え、  
**品質・製造・監査・ダッシュボード用途に強い UI を安定生成するための実務向けプロトコル集**です。

## 目的
- AI に「見た目の指示」ではなく **判断基準** を渡す
- Codex / Claude Code / Antigravity / Copilot 等で再利用できる形にする
- Portal / 社内ツール / React UI に適用できるようにする
- 「TODO 残し」「仮データ逃げ」「派手だが使いにくい UI」を防ぐ

## 同梱物
- `01_core_skills/`
  - Taste Skill 本体
  - Audit Skill
  - Output Skill
  - Portal / Dashboard / QA 監査向け派生版
- `02_agent_protocols/`
  - Codex CLI 向け投入文
  - Claude Code 向け投入文
  - Antigravity 向け投入文
  - GitHub Copilot / Cursor 向け投入文
- `03_templates/`
  - 要件定義テンプレート
  - UIレビュー票
  - PRレビュー観点
- `04_examples/`
  - React ダッシュボード生成例
  - 監査アプリ生成例
- `05_portal_integration/`
  - Portal カード化の進め方
  - 既存環境への組み込み方針
- `06_adoption_checklists/`
  - 導入前チェック
  - 導入後チェック
  - NG例
- `07_optional_starters/`
  - system prompt 雛形
  - task prompt 雛形
  - review prompt 雛形
- `80_reports/`
  - 提案書ドラフト
  - 導入判断メモ
- `90_archive/`
  - 変更しない原本用メモ

## 使い方（最短）
1. `01_core_skills/QA_UI_TASTE_SKILL_v1.md`
2. `01_core_skills/QA_UI_AUDIT_SKILL_v1.md`
3. `01_core_skills/STRICT_OUTPUT_RULE_v1.md`
4. `02_agent_protocols/` の該当エージェント用投入文

を AI に順番に読み込ませてください。

## 想定用途
- 品質ダッシュボード
- 検査結果画面
- トレーサビリティ画面
- IATF / 内部監査支援 UI
- 製造条件監視 UI
- 不良分析ビューア
- Portal カード形式の業務アプリ

## 注意
この ZIP は **プロトコル / ルール / テンプレート集**です。  
特定リポジトリに直接パッチを当てるものではありません。

必要に応じて、受け側 AI に次を指示してください。
- 既存 UI / 既存カード / Compose / 依存関係との競合確認
- 部分導入か全面導入かの判断
- 既存デザインシステムとの整合確認
