# INC-XLS-SPARSE-BLANK-CELL-20261113-01

Observed 2026-11-13 11:33–11:38 JST, K10, current authorized spreadsheet-format-preservation task. Owner: current Codex task. Source files and unrelated processes were preserved.

## Facts, cause, impact and recovery
A native legacy-workbook edit preflight stopped because visually blank cells in later formatted rows had no explicit BIFF cell records. The initial writer assumed every target already had a record. This cause is confirmed by the missing-cell coordinate assertion. The guard fired before the output copy/write stage, so no partial deliverable or source mutation occurred. Prior legacy extraction incident: INC-XLS-TIME-SERIALIZATION-20261113-01.

The writer now distinguishes absent cell records from existing blank records, inserts only required values and styles in row/column order, and retains the source's native style definitions and all non-workbook OLE streams. Legacy cell-block cache offsets are removed only for the edited sheet and adjusted for relocated unedited sheets. No OLE stream resizing or macro execution is used. Recovery remains bounded and explicitly refuses overwriting a previous deliverable.

Verification: all three sheets were re-read with an independent legacy-workbook parser; every value outside the explicit change list, all original global style/font/palette/shared-string/name records, row heights, column widths, merges, formulas, print/drawing records and macro/other stream hashes were checked. A second office engine loaded a validation copy and produced a reference conversion whose changed cells were re-read. Original/updated visible ranges were compared; the final deliverable remains native legacy format. The original source and the supporting primary records were rehashed before editing. Limit: validation conversion is a disposable reference and is never substituted for the native deliverable.

## FMEA draft revision 1
Failure: sparse blank cell assumed to exist. Effect: native edit cannot complete; without a guard, a missing target could be silently omitted. Confirmed cause: record-presence assumption. Prevention: explicit target-coverage set, sparse insertion, no-overwrite output guard. Detection: changed-coordinate coverage assertion, exact cell/style readback, independent office-engine readback. Owner: current implementation; future owner unassigned. Residual risk: other legacy record types remain unsupported until explicitly verified. S/O/D/RPN unassessed.

## FTA draft revision 1
Top event: incomplete or format-damaged legacy spreadsheet update. OR branches: missing sparse cell (confirmed, preflight contained), incorrect shared-style mutation (checked absent), broken relocated cached offsets (independent readback checked), unintended macro/other-stream alteration (hash checked absent), unrelated source change (hash gate). Unchecked workbook variants remain unresolved rather than assumed compatible.

## QC process chart draft revision 1
Fresh source hashes -> explicit update list -> record coverage preflight -> isolated native copy/write -> complete value/style/stream verification -> independent native-reader check -> visible-range review -> delivery hash check. Acceptance: all target coordinates present, unrelated content preserved, original hash unchanged. Failure reaction: stop before publication, preserve evidence, repair only the owned writer, and rerun the explicit verification.

## Control Plan draft revision 1
Characteristics: sparse-record coverage, native formatting, VBA integrity, source/destination identity. Methods: set equality; exact global records and style-index checks; non-workbook stream SHA256; source/delivery SHA256. Timing: every native edit and immediately before delivery. Limits: exact expected coordinates/records/hashes; no invented engineering tolerance. Reaction: hold deliverable, retain originals and known-good output, fix the scoped writer. Owner: current task; future owner unassigned. Effectiveness: preflight actually prevented a partial write; patched output passed parser, second-engine and visual checks. Documentation alone does not establish general compatibility.

This sanitized card excludes workbook values, engineering drawings, personal paths, credentials and private raw logs. Knowledge destinations have separate receipts. Satellite snapshots require fresh target identity checks and are unattempted for this task.
