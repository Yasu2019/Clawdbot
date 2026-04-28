# MQTTトピック設計

## 推奨トピック

```text
press/{machine_id}/telemetry
press/{machine_id}/status
vision/{line_id}/inspection/request
vision/{line_id}/inspection/result
```

## press telemetry payload

```json
{
  "machine_id": "AMADA80T-3",
  "timestamp": "2026-04-28T10:00:00+09:00",
  "shot": 123456,
  "spm": 55,
  "chokotei": 2,
  "jyotai": 1
}
```

## vision result payload

```json
{
  "inspection_id": "uuid",
  "part_no": "品番",
  "lot_no": "Lot",
  "judgement": "OK候補 | NG候補 | 判定不能",
  "defect_candidates": ["キズ"],
  "confidence": 0.82,
  "human_review_required": true
}
```
