# AI Video Control Protocol - Honki Edition

このパッケージは、AI生成動画の「AI臭」を減らし、人間主導で動画品質を制御するための実務向けプロトコル集です。

## 含まれるもの
- 00_README_FIRST.md
- 01_MASTER_PROTOCOL_JA.md
- 02_MASTER_PROTOCOL_EN.txt
- 03_JSON_SCHEMA_TEMPLATE.json
- 04_SCENE_PROMPT_EXAMPLES.json
- 05_PRODUCTION_WORKFLOW_CHECKLIST.md
- 06_QA_REVIEW_SHEET.csv
- 07_DIFF_REVISION_RULES.md
- 08_LOCAL_APP_CONCEPT.md
- 09_CLAUDE_CODE_HANDOFF_PROTOCOL.txt
- 10_CODE_SAMPLES/
  - prompt_builder.py
  - motion_review_checklist.py
  - simple_shot_manifest.json

## 目的
1. プロンプトを構造化して再現性を上げる
2. 開始・終了ポーズを固定して構図崩れを抑える
3. 人間モーションを使って身体性を改善する
4. 差分レビューで修正を局所化する
5. 将来的にローカル/半自動パイプラインへ拡張する

## 推奨利用順
1. 01_MASTER_PROTOCOL_JA.md を読む
2. 03_JSON_SCHEMA_TEMPLATE.json をコピーして案件化
3. 04_SCENE_PROMPT_EXAMPLES.json を参考に構造入力
4. 05_PRODUCTION_WORKFLOW_CHECKLIST.md で制作
5. 06_QA_REVIEW_SHEET.csv でレビュー
6. 必要に応じ 09_CLAUDE_CODE_HANDOFF_PROTOCOL.txt をAI開発エージェントへ渡す
