# 06. n8n ワークフロー設計

## WF-01 LEARNING__INGEST_NEW_CASE
用途:
- 手動JSONやCSV変換後JSONを投入

流れ:
1. Trigger
2. Read File
3. Parse
4. POST `/ingest/case`
5. 成功時 archive

## WF-02 LEARNING__COMPARE_NEW_CASE
用途:
- 新規品質案件の類似比較

流れ:
1. Trigger from WF-01
2. POST `/compare/case`
3. high risk なら通知
4. 結果ファイル保存

## WF-03 LEARNING__EMAIL_INGEST_EML
用途:
- `/local_emails/**/*.eml` 監視

流れ:
1. Local File Trigger
2. Read Binary
3. EML parse
4. LLM structured extract
5. POST `/ingest/email-message`

## WF-04 LEARNING__EMAIL_THREAD_SUMMARIZE
用途:
- thread 単位要約

流れ:
1. Scheduler
2. 未集約message取得
3. thread grouping
4. POST `/ingest/email-thread`
5. POST `/compare/email-thread`

## WF-05 LEARNING__QUALITY_ISSUE_IMPORT
用途:
- 是正処置や改善活動の取込

流れ:
1. Folder / API / CSV trigger
2. Normalization
3. POST `/ingest/quality-issue` or `/ingest/improvement-activity`

## WF-06 LEARNING__CAE_RUN_IMPORT
用途:
- CAE run 結果取込

流れ:
1. Folder watch (`/work/cae_runs/**/*.json`, `*.log`, `*.md`)
2. Parse
3. Error signature extraction
4. POST `/ingest/cae-run`
5. 失敗なら `/compare/cae-run`

## WF-07 LEARNING__REVIEW_FEEDBACK
用途:
- 人レビュー反映

流れ:
1. Manual/Webhook
2. POST `/feedback/judgement`

## WF-08 LEARNING__LESSON_GENERALIZE
用途:
- former employer data から一般教訓を抽出

流れ:
1. reviewed raw memory fetch
2. anonymize
3. abstraction prompt
4. save to `lesson_memory`
