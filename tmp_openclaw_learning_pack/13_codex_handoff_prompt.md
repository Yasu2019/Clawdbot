# Codex / Antigravity 引き渡し用プロンプト

既存の Clawstack / OpenClaw Docker 環境に、疑似 Nested Learning を追加してください。

## 目的
- 品質問題点
- 改善活動
- Email
- CAE/FEM の成功失敗経験

を外部記憶として蓄積し、次回の比較判断に再利用できるようにする。

## 実装条件
1. 既存 compose を大きく壊さない
2. 新規中核サービスは `learning_engine`
3. learning_engine は FastAPI
4. Qdrant, LiteLLM, Langfuse, n8n を既存内部URLで利用
5. 以下の API を実装
   - GET /health
   - POST /ingest/case
   - POST /ingest/email-message
   - POST /ingest/email-thread
   - POST /ingest/quality-issue
   - POST /ingest/improvement-activity
   - POST /ingest/cae-run
   - POST /compare/case
   - POST /compare/email-thread
   - POST /compare/cae-run
   - POST /feedback/judgement
   - POST /search/memory
6. Qdrant コレクションを実装
   - lot_event_memory
   - defect_case_memory
   - plating_reflow_memory
   - pfmea_memory
   - dr_meeting_memory
   - judgement_memory
   - email_thread_memory
   - email_fact_memory
   - email_judgement_memory
   - quality_issue_memory
   - improvement_activity_memory
   - lesson_memory
   - cae_run_memory
   - cae_failure_memory
   - cae_success_pattern_memory
   - cae_lesson_memory
7. former employer data の raw と current company data の raw は分離し、cross-org はデフォルトで無効
8. `lesson_memory` のみ匿名化一般教訓として cross-org 再利用可
9. Portal に `Learning Memory` カードを追加
10. n8n ワークフローを追加
    - LEARNING__INGEST_NEW_CASE
    - LEARNING__COMPARE_NEW_CASE
    - LEARNING__EMAIL_INGEST_EML
    - LEARNING__EMAIL_THREAD_SUMMARIZE
    - LEARNING__QUALITY_ISSUE_IMPORT
    - LEARNING__CAE_RUN_IMPORT
    - LEARNING__REVIEW_FEEDBACK
    - LEARNING__LESSON_GENERALIZE

## 特に重要
- Email は相手が本当に欲しい回答、未回答論点、添付との整合まで扱う
- 品質問題点は lot, defect, containment, suspected root cause, permanent action を保持
- 改善活動は before/after, expected/measured effect を保持
- CAE/FEM は success / failure 両方を蓄積し、error_signature と有効だった修正を残す
- 人レビューを必須化し、AI判断を鵜呑みにしない
