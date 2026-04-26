# Antigravity 向け投入プロトコル（Taste Skill 本気版）

## 目的
Taste Skill を、設計 → 実装 → 監査 の 3段階に分けて適用する。

## 推奨パイプライン

### Stage 1: DESIGN
入力:
- 要件
- QA_UI_TASTE_SKILL_v1.md
- PORTAL_CARD_TASTE_SKILL_v1.md（必要時）

出力:
- 画面目的
- ユーザー判断タスク
- 画面構成
- コンポーネント一覧
- 状態一覧

### Stage 2: BUILD
入力:
- Stage 1 出力
- STRICT_OUTPUT_RULE_v1.md

出力:
- 完全コード
- エラー状態 / 空状態 / 読み込み状態込み

### Stage 3: AUDIT
入力:
- Stage 2 出力
- QA_UI_AUDIT_SKILL_v1.md

出力:
- 問題点
- 改修提案
- 必要なら再生成

## 運用ルール
- 各段階で判断理由を保存
- 既存 Portal / カード / コンポーネントと競合確認
- 重大指摘があれば BUILD に戻す
- 完了条件を曖昧にしない
