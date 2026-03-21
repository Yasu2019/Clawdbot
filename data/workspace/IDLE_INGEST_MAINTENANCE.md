# Idle Ingest Maintenance

ローカルLLMが直接のユーザー作業を持っていないときは、以下の低優先メンテナンスを行う。

## 実行入口

- heartbeat: `data/workspace/HEARTBEAT.md`
- n8n fallback workflow: `Idle Ingest Maintenance (Every 3h)`
- external harness: `data/workspace/idle_ingest_maintenance.py`

## 実行対象

- Email RAG ingest の鮮度確認と、8時間以上古い場合のみ再実行
- Scheduled reports の DB 同期が古い場合の再同期
- Cmux status JSON が古い場合の再生成

## 状態ファイル

- `data/workspace/idle_ingest_maintenance_status.json`

## しきい値

- email ingest: 8時間
- scheduled report sync: 2時間
- cmux status: 1時間

## 目的

- ローカルLLMの待機時間を、静かな保守作業に使う
- 重要な ingest / index / status を止めない
- ただし不要な通知スパムは出さない

