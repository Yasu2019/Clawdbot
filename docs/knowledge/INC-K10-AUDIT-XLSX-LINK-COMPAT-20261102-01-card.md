# XLSX audit-evidence export compatibility near miss

Incident INC-K10-AUDIT-XLSX-LINK-COMPAT-20261102-01; observed and contained on K10 on 2026-11-02, approximately 12:59–13:06 JST. No source workbook was edited and no flawed workbook was delivered.

Observed failures: a trailing-space worksheet name was rejected during rendering; a documented hyperlink formula rendered diagnostic text instead of its label; and a normal exporter roundtrip did not preserve an original frozen view. Internal implementation causes remain UNKNOWN. Help text and a successful export were insufficient evidence of native feature correctness.

Correction: normalize only an intermediate working copy where required, author additions with the spreadsheet tool, create standard native OOXML hyperlink records for the missing capability, and transplant only the authored additions into the original package. Preserve original sheet names, values/formulas, native objects and views. Do not rewrite source workbooks or stage unrelated working-tree changes.

Validation passed: original nonempty values/formulas, charts/merges/validations/freeze panes; every added hyperlink target; selected source-file hashes; visual inspection; native application load/save; and hash equality of delivered copies. Explicitly mark missing evidence and extraction limitations. Native application verification retained all added links and the original aggregate results.

Prevent recurrence by requiring actual display-label checks, native hyperlink records, exact preservation comparisons and a native load/save check before delivery. A rendered preview, help entry or formula string alone is not proof. FMEA, FTA, QC process chart and Control Plan drafts link the same incident; scoring and formal owner assignments remain unassessed. Private business text and raw execution logs are intentionally excluded from this card.
