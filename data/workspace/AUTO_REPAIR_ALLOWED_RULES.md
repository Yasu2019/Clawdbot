# Auto Repair Allowed Rules

Last updated: 2026-03-29 JST

## 目的

低リスクで自動修復してよい不具合を、外付けハーネスとして定義する。

実装:
- [`auto_repair_allowed.py`](/D:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed.py)
- [`idle_ingest_maintenance.py`](/D:/Clawdbot_Docker_20260125/data/workspace/idle_ingest_maintenance.py)

## 現在の自動修復対象

1. `scheduled_reports_sync`
- 症状:
  - stale
  - timed out
  - non-zero returncode
- 修復:
  - `scheduled_report_search.py sync --limit-executions 20`

2. `cae_learning_sync`
- 症状:
  - `stage=skipped`
  - `learning_engine unavailable`
  - stale
- 修復:
  - `sync_cae_learning_memory.py --base-url http://localhost:8110 --source-org Mitsui`
  - script 内で `localhost / host.docker.internal / 127.0.0.1` を自動フォールバック

3. `email_rag_ingest_runtime`
- 症状:
  - timed out
  - 2時間以上 stuck
- 修復:
  - `run_email_rag_ingest_report.py` を再起動
  - ただし既に同名プロセスが動いている場合は二重起動しない

## 実行タイミング

- `idle_ingest_maintenance.py` の最後に毎回実行
- status 出力:
  - [`auto_repair_allowed_status.json`](/D:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed_status.json)

## あえて自動化していないもの

- 商用 SDK 導入
- compose の大規模整理
- GPU / 大型サービス停止
- cross-org データ方針変更
- UI 文言や業務ルールの変更

## 方針

`自動検知 + 低リスク修復のみ自動実行`

高リスク変更は、引き続き人またはエージェントが状況を見て判断する。
