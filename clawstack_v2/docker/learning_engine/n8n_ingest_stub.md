# Learning Engine n8n Ingest Stub

Use these example HTTP requests when wiring `n8n` to the new learning memory service.

## Base URL

- `http://learning_engine:8000` inside Docker compose
- `http://localhost:8110` from the host after activating the compose patch

## Quality Issue Ingest

`POST /ingest/quality-issue`

Example JSON:

```json
{
  "issue_id": "qi-2026-001",
  "source_org": "Mitsui",
  "source_type": "n8n",
  "review_status": "reviewed",
  "title": "Plating discoloration recurrence from lot complaint",
  "lot_no": "251201",
  "part_number": "NT3621-P44",
  "process": "plating",
  "defect_name": "discoloration",
  "summary": "Brown discoloration found after shipment feedback",
  "containment_action": "isolate lot and inspect stock",
  "suspected_root_cause": "bath chemistry drift",
  "permanent_action": "tighten chemistry control",
  "owner": "quality-team",
  "status": "open"
}
```

## Email Message Ingest

`POST /ingest/email-message`

Example JSON:

```json
{
  "message_id": "msg-2026-001",
  "thread_id": "thread-2026-042",
  "source_org": "Mitsui",
  "source_type": "n8n",
  "review_status": "reviewed",
  "subject": "Customer complaint follow-up for discoloration lot",
  "sender": "qa@example.com",
  "recipients": ["me@example.com", "supplier@example.com"],
  "sent_at": "2026-03-27T09:15:00+09:00",
  "summary": "Customer asked for root cause and shipment decision.",
  "body_excerpt": "Please confirm the containment result and permanent action.",
  "extracted_facts": [
    "Lot 251201 is affected",
    "Shipment hold requested"
  ],
  "open_questions": [
    "Can the lot be released?",
    "When will 8D be shared?"
  ],
  "latest_status": "awaiting supplier response"
}
```

## Email Thread Ingest

`POST /ingest/email-thread`

Example JSON:

```json
{
  "thread_id": "thread-2026-042",
  "source_org": "Mitsui",
  "source_type": "n8n",
  "review_status": "reviewed",
  "subject": "Customer complaint follow-up for discoloration lot",
  "participants": ["qa@example.com", "supplier@example.com", "sales@example.com"],
  "summary": "Thread tracks shipment hold, root cause discussion, and 8D timing.",
  "open_questions": [
    "Can the lot be released?",
    "When will 8D be shared?"
  ],
  "latest_status": "supplier preparing 8D draft",
  "next_action": "review supplier 8D and decide shipment hold"
}
```

## Improvement Activity Ingest

`POST /ingest/improvement-activity`

Example JSON:

```json
{
  "activity_id": "ia-2026-001",
  "source_org": "Mitsui",
  "source_type": "n8n",
  "review_status": "reviewed",
  "title": "Inspection rule update for emboss tape process",
  "summary": "Added measured judgement rule after recurring scratches",
  "target_process": "emboss tape",
  "trigger_issue": "scratch recurrence",
  "before_state": "visual judgement only",
  "after_state": "measured threshold with checklist",
  "change_type": "inspection_control",
  "expected_effect": "reduce escapes",
  "measured_effect": "customer complaints reduced to zero for two weeks",
  "result_status": "effective",
  "owner": "manufacturing-engineering"
}
```

## CAE Run Ingest

`POST /ingest/cae-run`

Example JSON:

```json
{
  "run_id": "cae-2026-0001",
  "source_org": "Mitsui",
  "source_type": "n8n",
  "review_status": "reviewed",
  "tool_name": "OpenRadioss",
  "tool_version": "OpenRadioss 2026",
  "simulation_type": "leveler_contact",
  "project_name": "4mmx4mm_ASSY_20260105",
  "mesh_size": "4mm",
  "time_step": "2.0788E-09",
  "solver_settings": "explicit structural",
  "result_status": "success",
  "error_signature": "stable_explicit_progress",
  "wall_clock_time": "1501.88 s",
  "summary": "OpenRadioss run progressed stably with animation outputs written.",
  "lesson": "Stable time-step progression maintained through the observed log window."
}
```
