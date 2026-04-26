# IATF DB Seed Update Method

## Purpose

This note records how IATF document data is currently updated so the same data can be migrated to another PC with `db:seed`, and so a future auto-diff updater can follow the same rules.

## Current source-of-truth split

- Live Rails app data:
  - container volume `db/record/attachedfile.csv`
  - container/volume-backed `db/documents`
- Seed and migration source on host:
  - [`iatf_system/db/record/attachedfile.csv`](D:/Clawdbot_Docker_20260125/iatf_system/db/record/attachedfile.csv)
  - [`iatf_system/db/documents`](D:/Clawdbot_Docker_20260125/iatf_system/db/documents)

The host-side files are the migration-safe copies. They must be kept in sync with the live container state before moving the system to another PC.

## Current update flows

### 1. Sync live production data back to seed source

Script:
- [`sync_iatf_seed_assets.py`](D:/Clawdbot_Docker_20260125/data/workspace/sync_iatf_seed_assets.py)

What it does:
- exports live `attachedfile.csv` from `iatf_system-web-1`
- writes it to host `iatf_system/db/record/attachedfile.csv`
- fills missing host documents from `data/state/IATF_documents` when possible
- writes status to `iatf_seed_sync_status.json`
- appends an entry to `iatf_system/db/update_history.json`

### 2. Backfill JQA audit reports

Script:
- [`backfill_jqa_audit_reports.py`](D:/Clawdbot_Docker_20260125/data/workspace/backfill_jqa_audit_reports.py)

Service:
- [`jqa_audit_report_ingest_service.rb`](D:/Clawdbot_Docker_20260125/iatf_system/app/services/jqa_audit_report_ingest_service.rb)

Rules:
- `category = 2`
- `documentcategory = JQA審査報告書`
- `documentnumber = YYYY-JQA-XXX`
- `phase` and `stage` are left blank for now

### 3. Import manufacturing design ZIP files

Script:
- [`import_manufacturing_design_zip.py`](D:/Clawdbot_Docker_20260125/data/workspace/import_manufacturing_design_zip.py)

Service:
- [`attachedfile_seed_import_service.rb`](D:/Clawdbot_Docker_20260125/iatf_system/app/services/attachedfile_seed_import_service.rb)

Rules:
- `category = 1`
- `phase = 10`
- `stage`
  - `105`: 設計計画書
  - `106`: 設計検証チェックリスト
  - `112`: D.R会議議事録

## Update history page

Rails page:
- [`products/update_history`](http://localhost:3000/products/update_history)
- [`products/update_history`](http://localhost:3003/products/update_history)

Files:
- [`update_history_service.rb`](D:/Clawdbot_Docker_20260125/iatf_system/app/services/update_history_service.rb)
- [`update_history.html.erb`](D:/Clawdbot_Docker_20260125/iatf_system/app/views/products/update_history.html.erb)
- [`update_history_utils.py`](D:/Clawdbot_Docker_20260125/data/workspace/update_history_utils.py)

Rebuild script:
- [`rebuild_iatf_update_history.py`](D:/Clawdbot_Docker_20260125/data/workspace/rebuild_iatf_update_history.py)

## Planned auto-diff update design

Target behavior:
- inspect specific watch folders
- compare against host `attachedfile.csv`
- compare against host `db/documents`
- detect differences by:
  - filename
  - file size
  - last modified time if useful
- import only new or changed files
- append a readable entry to `update_history.json`

Recommended low-risk sequence:
1. scan watched folders and build manifest
2. scan `attachedfile.csv` and `db/documents`
3. classify files as `new`, `changed`, `missing_document`, `already_synced`
4. write a dry-run status JSON first
5. only then apply the update
6. append one summarized history entry

## Implemented auto-diff harness

Script:
- [`iatf_seed_auto_update.py`](D:/Clawdbot_Docker_20260125/data/workspace/iatf_seed_auto_update.py)

Current watch targets:
- [`clawstack_v2/data/paperless/consume/審査報告書`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/paperless/consume/%E5%AF%A9%E6%9F%BB%E5%A0%B1%E5%91%8A%E6%9B%B8)
- [`clawstack_v2/data/paperless/consume/製造工程設計`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/paperless/consume/%E8%A3%BD%E9%80%A0%E5%B7%A5%E7%A8%8B%E8%A8%AD%E8%A8%88)

Modes:
- dry run:
  - detects `new`
  - detects `missing_csv_only`
  - detects `missing_document_only`
  - detects `changed_existing` by file size
- apply:
  - auto-imports `new`
  - auto-repairs `missing_csv_only`
  - auto-restores `missing_document_only`
  - does **not** overwrite `changed_existing` in DB automatically

Reason for the `changed_existing` rule:
- replacing already-attached Rails documents is higher risk than adding new ones
- those items are logged for review instead of being overwritten silently

Status file:
- [`iatf_seed_auto_update_status.json`](D:/Clawdbot_Docker_20260125/data/workspace/iatf_seed_auto_update_status.json)

## Important caution

Do not treat the host `attachedfile.csv` as the live runtime database unless the latest sync has been run.
The host copy is the migration-safe seed source, not always the current runtime source.

## Additional seed import flow: document reconciliation Excel assets

Script:
- [`import_document_reconciliation_seed_assets.py`](D:/Clawdbot_Docker_20260125/data/workspace/import_document_reconciliation_seed_assets.py)

Rules:
- `category = 2`
- `documentcategory = 文書照合資料`
- `documentnumber = DOCREC-20250329-XXX`
- `phase` and `stage` are left blank

What it does:
- extracts only `.xls` / `.xlsx` files from `文書照合_20250329.zip`
- appends them to host seed [`attachedfile.csv`](D:/Clawdbot_Docker_20260125/iatf_system/db/record/attachedfile.csv)
- copies them to host seed [`db/documents`](D:/Clawdbot_Docker_20260125/iatf_system/db/documents)
- mirrors them to `data/state/IATF_documents`
- writes status to `document_reconciliation_seed_import_status.json`

## Additional seed import flow: supplier Excel assets

Script:
- [`import_supplier_seed_assets.py`](D:/Clawdbot_Docker_20260125/data/workspace/import_supplier_seed_assets.py)

Rules:
- `category = 2`
- `documentcategory`
  - `供給者リスト`
  - `供給者管理計画実績`
  - `供給者評価再評価台帳`
- `documentnumber = SUPPLIER-20260329-XXX`
- `phase` and `stage` are left blank

What it does:
- copies the 3 supplier Excel source files from `Supplier_20260329`
- appends them to host seed [`attachedfile.csv`](D:/Clawdbot_Docker_20260125/iatf_system/db/record/attachedfile.csv)
- copies them to host seed [`db/documents`](D:/Clawdbot_Docker_20260125/iatf_system/db/documents)
- mirrors them to `data/state/IATF_documents`
- writes status to `supplier_seed_import_status.json`

## Additional seed import flow: process monitoring measurement PDFs

Script:
- [`import_process_monitoring_measurement_seed_assets.py`](D:/Clawdbot_Docker_20260125/data/workspace/import_process_monitoring_measurement_seed_assets.py)

Rules:
- source folder: [`clawstack_v2/data/paperless/consume/IATF成果報告書`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/paperless/consume/IATF%E6%88%90%E6%9E%9C%E5%A0%B1%E5%91%8A%E6%9B%B8)
- target years: `2024`, `2025`, `2026`
- file type: `.pdf`
- `category = 2`
- `phase = 16`
- `stage = 343`
- `documentcategory = プロセスの監視・測定記録`
- `documentnumber = 9.1.3.1`

What it does:
- scans year subfolders under `IATF成果報告書`
- appends missing rows to host seed [`attachedfile.csv`](D:/Clawdbot_Docker_20260125/iatf_system/db/record/attachedfile.csv)
- copies missing PDFs to host seed [`db/documents`](D:/Clawdbot_Docker_20260125/iatf_system/db/documents)
- mirrors them to `data/state/IATF_documents`
- imports them into the live Rails DB via `AttachedfileSeedImportService`
- writes status to `process_monitoring_measurement_seed_import_status.json`
