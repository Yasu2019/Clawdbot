# 12. 実装順序

## Phase 1: 中核
1. learning_engine 作成
2. `/health`, `/ingest/case`, `/compare/case`, `/feedback/judgement`
3. Qdrant 基本コレクション作成

## Phase 2: Email
1. `/ingest/email-message`
2. `/ingest/email-thread`
3. `/compare/email-thread`
4. n8n の EML 取込

## Phase 3: 品質問題 / 改善活動
1. `/ingest/quality-issue`
2. `/ingest/improvement-activity`
3. lesson generalization

## Phase 4: CAE/FEM
1. `/ingest/cae-run`
2. `/compare/cae-run`
3. error_signature 抽出
4. CAE Lessons UI

## Phase 5: Portal / Review
1. learning_memory UI
2. Review Queue
3. reviewed / approved フィルタ

# 受入基準
- health が通る
- 新規品質案件から過去類似案件が返る
- Email thread から未回答論点が返る
- 改善活動が検索できる
- CAE failure から類似失敗と修正候補が返る
- former employer データが raw では cross-org 検索されない
- lesson_memory だけは cross-org で再利用できる
