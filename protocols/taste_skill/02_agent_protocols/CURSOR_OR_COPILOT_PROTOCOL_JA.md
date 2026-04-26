# Cursor / GitHub Copilot 向け投入プロトコル

以下の優先順位で適用してください。

1. QA_UI_TASTE_SKILL_v1.md
2. STRICT_OUTPUT_RULE_v1.md
3. QA_UI_AUDIT_SKILL_v1.md

## 目的
テンプレっぽい UI を避け、業務適合性の高い UI を安定して出す。

## 指示
- まず画面の主目的を 1 文で定義
- その目的に必要な判断項目を列挙
- その判断を最短で支援する UI を組む
- コードは省略せず出す
- 出力後に自分で監査する

## 禁止
- おしゃれ優先
- TODO 残し
- ダミー逃げ
- 理由なき余白 / 色 / グラフ
