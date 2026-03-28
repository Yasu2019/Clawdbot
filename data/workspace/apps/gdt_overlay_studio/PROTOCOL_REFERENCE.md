# Local LLM Supervision Protocol Reference

Reference source:
`D:\Clawdbot_Docker_20260125\local_llm_supervision_protocol_complete_utf8_bom.zip`

This note summarizes the protocol package for the current GD&T workflow so the app can evolve without re-reading the ZIP every time.

## Relevant package files

- `README.md`
- `01_master_protocol.md`
- `07_gdt_specific_rules.md`
- `08_success_criteria.md`
- `09_file_structure.md`

## Practical rules for this app

1. Keep a review loop between model input, drawing input, and generated GD&T overlay output.
2. Prefer explicit structured data for datum systems and tolerance zones.
3. Treat GD&T extraction and placement as a supervised workflow, not a blind fully automatic step.
4. Keep error handling visible so the operator can rework the result when datum reference, zone type, or placement is ambiguous.
5. Preserve intermediate artifacts that help review:
   - source model
   - source drawing
   - extracted datum data
   - extracted GD&T data
   - exported review JSON

## Success criteria mapped to the MVP

- The user can load a 3D model and a drawing in one workspace.
- Datum definitions can be created and edited explicitly.
- GD&T callouts can be created and edited explicitly.
- A saved session can be exported for review and reloaded later.
- Packed HTML generated elsewhere can be imported and reused.

## Suggested next-step features

- Semi-automatic detection of datum symbols and feature control frames from PDF or DXF.
- Review status fields such as `draft`, `reviewed`, and `approved`.
- Error taxonomy logging for failed or uncertain extractions.
- A side-by-side rework queue for ambiguous callouts.
