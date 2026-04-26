# QMS Audit Protocol Reference

Reference source:
`D:\Clawdbot_Docker_20260125\QMS_Audit_Protocol_Complete_WindowsSafe.zip`

This note summarizes the Windows-safe protocol bundle for the current QMS Audit Studio.

## Relevant package files

- `00_README_UTF8_BOM.md`
- `01_complete_protocol_utf8_bom.md`
- `03_existing_system_audit_utf8_bom.md`
- `05_integration_plan_utf8_bom.md`
- `06_implementation_checklist_utf8_bom.md`
- `99_windows_compatibility_note_utf8_bom.md`

## Practical rules for this app

1. Prefer rule-based local checks first.
2. Reuse existing audit assets before adding another parallel audit engine.
3. Keep Windows-safe file handling and UTF-8 friendly references.
4. Surface data quality issues clearly:
   - required column mismatch
   - blank fields
   - suspicious short text
   - invalid answer fields
   - duplicate choices
   - mojibake suspicion
5. Preserve audit output as a reviewable JSON artifact.

## Success criteria mapped to the current app

- The user can load one or more CSV files in the browser.
- The user can run a local audit without backend dependency.
- The report shows file count, row count, issue count, and worst file.
- The report can be exported as JSON.
- The app clearly points to the canonical Windows-safe protocol bundle.

## Suggested next-step features

- Better encoding guidance for CP932 vs UTF-8 CSV files.
- Severity grouping and remediation suggestions by issue type.
- Integration with existing Rails audit assets for deeper follow-up.
