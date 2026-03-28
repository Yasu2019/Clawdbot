# QMS Audit Paths

## Primary files

- `iatf_system/app/services/testmondai_quality_audit_service.rb`
- `data/workspace/audit_iatf_testmondai_quality.rb`
- `data/workspace/apps/qms_audit/index.html`
- `data/workspace/apps/learning_memory/index.html`

## Existing audit patterns

- `TestmondaiQualityAuditService` already checks:
  - required columns
  - blank question
  - short question
  - blank explanation
  - short explanation
  - invalid `seikai`
  - duplicate choices
  - mojibake suspicion
- `audit_iatf_testmondai_quality.rb` already writes JSON and Markdown reports.

## When to stay local

Stay browser-local or host-side when:

- input is just CSV
- checks are deterministic
- no OCR is needed
- no cross-document retrieval is needed

## When to expand

Consider OCR / RAG / learning memory only when:

- source files are PDFs or scans
- findings must connect to prior issues
- corrective action suggestions need memory retrieval
