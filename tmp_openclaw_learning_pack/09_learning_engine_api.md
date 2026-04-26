# 09. API 仕様

## GET /health
返却:
```json
{"status":"ok"}
```

## POST /ingest/case
品質案件の一般投入

## POST /ingest/email-message
1メール投入

## POST /ingest/email-thread
スレッド要約投入

## POST /ingest/quality-issue
品質問題点投入

入力例:
```json
{
  "issue_id": "qi-2026-001",
  "source_org": "Mitsui",
  "title": "めっき溶融ムラ",
  "lot_no": "251201",
  "part_number": "NT3621-P44",
  "process": "plating",
  "defect_name": "溶融ムラ",
  "summary": "顧客工程後に外観異常",
  "containment_action": "ロット隔離",
  "suspected_root_cause": "前処理変動の可能性",
  "permanent_action": "更新履歴と発生相関の再評価",
  "review_status": "draft"
}
```

## POST /ingest/improvement-activity
改善活動投入

## POST /ingest/cae-run
CAE/FEM 実行記録投入

入力例:
```json
{
  "run_id": "cae-2026-0001",
  "source_org": "Mitsui",
  "tool_name": "OpenRadioss",
  "simulation_type": "leveler_contact",
  "result_status": "failed",
  "failure_mode": "contact_penetration",
  "error_signature": "material flew away at first contact",
  "summary": "ローラー接触直後に材料が飛散",
  "lesson": "初期クリアランスと接触剛性を要見直し"
}
```

## POST /compare/case
品質案件比較

## POST /compare/email-thread
メール案件比較

## POST /compare/cae-run
CAE run 比較

## POST /feedback/judgement
人レビュー反映

## POST /search/memory
検索
オプション:
- `include_cross_org`
- `allowed_reuse_scope`
- `collections`
- `top_k`
