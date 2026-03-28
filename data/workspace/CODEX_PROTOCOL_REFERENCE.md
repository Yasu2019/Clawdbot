# Codex Protocol Reference

Updated: 2026-03-29 JST

## Source package

- Original ZIP:
  [`codex_protocol_package_report_template_utf8bom.zip`](/D:/Clawdbot_Docker_20260125/codex_protocol_package_report_template_utf8bom.zip)

## Purpose

This package is a reusable execution protocol for:

- repo survey before implementation
- merge / hold / new decision making
- detail design and DR preparation
- implementation sequencing
- final delivery report structure

## Most useful files

- `01_codex_master_protocol.md`
  - master execution order and safety rules
- `03_repo_survey_checklist.md`
  - survey-first checklist
- `04_decision_matrix.md`
  - adopt / integrate / hold / new build judgement
- `05_detail_design_and_dr_template.md`
  - design review template
- `11_codex_report_template.md`
  - final report structure

## Recommended use in this system

1. Use this pack before large feature work that may overlap with existing Portal, apps, or Docker services.
2. Prefer extending existing tools before building parallel apps.
3. Reuse the report template when delivering new app or protocol integrations.

## Current integration status

- Portal reference hub: planned and linked
- PDCA Lab: compatible with the same survey-first workflow
- Future candidates:
  - DXF to FCStd
  - QMS Audit
  - GD&T Overlay Studio
  - Kinematics Hub
