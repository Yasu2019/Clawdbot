# OpenClaw統合計画

## Goal
OpenClawに「AIアウトプット強化エンジン」を追加し、一般論回答を現場固有の120点回答へ変換する。

## Modules
1. sanpo_engine: 一般論→現場情報→再提案
2. persuasion_engine: Logos/Pathos/Ethos変換
3. qa_rag_router: IATF・社内標準・過去トラブル参照
4. report_writer: 報告書/メール/是正処置案生成
5. training_mode: 社内教育用問題生成

## Safety
- 勝手なファイル上書き禁止
- GitHubバックアップ後に大変更
- API消費最小、local LLM優先
- RAG根拠の明示
