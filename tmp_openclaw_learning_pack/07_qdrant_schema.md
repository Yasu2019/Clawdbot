# 07. Qdrant コレクション設計

## 7.1 初期コレクション一覧
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

## 7.2 全コレクション共通 payload
```json
{
  "memory_type": "defect_case",
  "source_org": "Mitsui",
  "source_type": "email|paperless|manual|csv|meeting|cae_log",
  "source_file": "example.pdf",
  "confidentiality": "internal",
  "reuse_scope": "same_org_only",
  "review_status": "draft",
  "created_at": "2026-03-26T10:00:00+09:00",
  "updated_at": "2026-03-26T10:00:00+09:00",
  "tags": ["plating", "reflow"]
}
```

## 7.3 judgement_memory 追加項目
- judgement_type
- input_case_id
- related_case_ids
- decision_summary
- confidence
- next_action
- human_feedback
- actual_outcome
- trace_id

## 7.4 Email 用追加項目
- thread_id
- subject
- participants
- open_questions
- latest_status

## 7.5 CAE 用追加項目
- tool_name
- tool_version
- simulation_type
- error_signature
- result_status
- failure_mode
- solver_settings
- mesh_size

## 7.6 検索デフォルト
- `include_cross_org=false`
- `review_status in [reviewed, approved]` を優先
- `lesson_memory` は cross-org 比較に使用可
