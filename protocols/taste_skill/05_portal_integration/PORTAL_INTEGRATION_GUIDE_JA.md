# Portal 組み込みガイド（Taste Skill版）

## 目的
Taste Skill を単なるプロンプトで終わらせず、
Portal / 社内 UI 標準として再利用可能にする。

## 推奨配置
- docs/ui-rules/taste/
  - QA_UI_TASTE_SKILL_v1.md
  - QA_UI_AUDIT_SKILL_v1.md
  - STRICT_OUTPUT_RULE_v1.md
  - PORTAL_CARD_TASTE_SKILL_v1.md

## 推奨運用
1. 新規カード作成時に Taste Skill を参照
2. 実装後に Audit Skill で自己監査
3. PR レビューでチェックリスト適用
4. 採用した UI パターンをサンプル化

## 既存環境への適用
- いきなり全面置換しない
- まず 1〜2 画面で試行
- 効果測定項目を決める
  - 修正回数
  - レビュー指摘数
  - 画面理解時間
  - 現場の使いやすさ評価

## 競合確認ポイント
- 既存デザインシステム有無
- Tailwind / shadcn/ui 採用状況
- Portal カード粒度
- 既存 KPI カード様式
- 既存配色ルール
