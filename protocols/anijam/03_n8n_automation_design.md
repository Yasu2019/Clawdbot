# 03 n8n Automation Design

## 目的
社内資料から動画化候補を抽出し、Anijam投入用データを自動生成する。

## 自動化対象
- 新規アップロード文書の検知
- 文書分類
- 要点抽出
- 動画化可否判定
- 台本生成
- プロンプト生成
- レビュー待ちキュー登録

## 推奨フロー
1. Trigger: Paperless or watched folder
2. Extract text
3. Chunking
4. Embedding / RAG search
5. LLM summarization
6. Video type classification
7. Script generation
8. Prompt package generation
9. Save JSON bundle
10. Notify reviewer

## 出力物
- script.md
- scenes.json
- anijam_prompt.txt
- review_checklist.md

## 人間承認ポイント
- Confidential 判定
- Customer name 判定
- 規格・数値整合性
- 社外共有可否
