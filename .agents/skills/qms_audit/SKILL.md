---
name: qms_audit
description: "Use when working on QMS, IATF, audit, checklist, CSV quality checks, or audit UIs in this project. Inspect the existing Rails audit assets and browser audit app first, prefer rule-based checks before OCR/RAG, and reuse testmondai_quality_audit_service patterns."
---

# QMS Audit Skill

Use this skill for QMS audit pages, IATF quiz CSV checks, rule-based audit flows, and lightweight compliance review tools.

## Workflow

1. Confirm whether the task should reuse existing assets:
   - `iatf_system/app/services/testmondai_quality_audit_service.rb`
   - `data/workspace/audit_iatf_testmondai_quality.rb`
   - `data/workspace/apps/qms_audit/`
2. Decide the audit mode:
   - browser-local rule audit
   - Rails-side audit reuse
   - future OCR/RAG extension
3. For small safe rollouts, prefer browser-local or host-side logic first.
4. Keep checks explainable:
   - required columns
   - blank / short fields
   - invalid answer markers
   - duplicate choices
   - mojibake suspicion
5. If integrating with broader memory or QMS flows, inspect `learning_engine` only after the rule-only path is clear.

## Rules

- Prefer rule-based first.
- Do not add unnecessary backend services for simple CSV audit tasks.
- Keep outputs explainable and exportable as JSON or Markdown where possible.
- Reuse existing IATF terminology and file conventions.

## Read next

- For key paths and checks: `references/qms_paths.md`
