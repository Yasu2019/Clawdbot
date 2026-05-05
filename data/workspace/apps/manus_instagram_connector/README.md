# OpenClaw × Manus × Instagram 品質保証付きSNS運用 本気版 V1

作成日: 2026-05-03  
バージョン: 1.0.0  
対象: OpenClaw / Clawstack V2 / WindowsミニPC / Claude Code / Codex / OpenCodeGO / Manus Instagram Connector

## 目的

このZIPは、ManusのInstagram Connectorをそのまま無条件に導入するものではありません。  
ミニパソコン側のClaudeが、既存のOpenClaw/Clawstack環境を確認したうえで、次のどれかを判断できるようにするための「評価・統合プロトコル」です。

- 採用
- 部分採用
- 保留
- 却下
- 追加調査後に再評価

## 最重要方針

1. 既存Clawstackを壊さない。
2. Docker volume、PostgreSQL、Qdrant、Minio、Redis、Ollama、Portal設定を勝手に変更しない。
3. Instagramは公式API・公式Connector・正規権限のみを使う。
4. スクレイピング、非公式ログイン自動化、認証情報の保存、規約違反の自動操作は禁止。
5. 投稿は完全自動化せず、必ず人間承認を挟む。
6. AI生成物は、誤情報、著作権、景表法、薬機法、ステマ、過剰表現、個人情報の観点でチェックする。
7. Claude/Codexは、このZIPを「実行指示」ではなく「判断材料」として扱う。

## 使い方

### 1. ミニパソコン側Claudeに最初に読ませるファイル

`00_CLAUDE_README_FIRST.md`

### 2. 既存環境を壊さず確認する

`10_scripts/audit_clawstack_readonly.ps1`  
`10_scripts/collect_env_readonly.py`

どちらも読み取り専用を前提にしています。実行前にClaude/Codexが内容を確認してください。

### 3. 採用判断を記録する

`12_decision/adoption_review_form.md`  
`12_decision/decision_matrix.md`  
`09_configs/adoption_decision_schema.json`

### 4. Portalカード案

`09_configs/portal_card.manus_instagram.json`

これは案です。既存Portal実装に合わせて、Claude/Codexが統合可否を判断してください。

## ZIP内の主要構成

- `01_strategy/`  
  SNS運用・収益化・ジャンル戦略
- `02_architecture/`  
  OpenClaw/Manus/Instagramの安全統合構成
- `03_safety/`  
  規約・個人情報・過剰自動化・誇大広告対策
- `04_workflows/`  
  競合分析、投稿カレンダー、投稿前レビュー、週次改善
- `05_prompts/`  
  Manus、Claude、Codex、OpenCodeGO向けプロンプト
- `09_configs/`  
  Portalカード、判定スキーマ、安全ポリシー
- `10_scripts/`  
  読み取り専用監査、投稿文チェック、週次レポート生成
- `11_templates/`  
  CSV/Markdownテンプレート
- `12_decision/`  
  ミニPC側Claudeが採否を決めるための資料
- `13_tests/`  
  破壊的コマンドが混入していないかを最低限確認するテスト

## 注意

このZIPは、Instagram運用の完全自動投稿を推奨しません。  
安全な基本形は以下です。

Manusで生成 → OpenClawで記録 → 人間が確認 → 承認済みだけ投稿/予約 → インサイト分析 → 次週改善

