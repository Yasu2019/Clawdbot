# INC-XLS-TIME-SERIALIZATION-20261113-01

Observed 2026-11-13 06:18–06:24 JST on K10 during an authorized read-only legacy spreadsheet reconciliation. Owner: current Codex task; unrelated calculations and monitoring were preserved.

## Facts and impact
The first extraction completed its file reads but failed when serializing a native time-only cell to JSON. The cause is confirmed: the serializer supported date and datetime but omitted time. No source workbook was modified. The failed attempt did not create the final JSON; an earlier count-only progress file could not recover the extraction payload. A later OCR helper had a PowerShell parse error before running; the helper was corrected with explicit loops. During reconciliation validation, a drawing-code tokenizer was found to drop an alphabetic prefix before a hyphen. This could incorrectly merge prefixed and unprefixed identifiers; the final comparison was rebuilt after correcting the tokenizer.

## Changes and verification
Support time-only values explicitly, use defensive JSON serialization, and persist one extraction record at a time to a separate recovery NDJSON. The rerun completed 2,171 non-trial-name files and eight encrypted-source read errors were retained explicitly. Source snapshot hashes and read-before/after file statistics were retained locally; the planned workbook hash was unchanged. Tokenizer assertions distinguish a prefixed synthetic identifier from its unprefixed identifier. OCR completed 29 images without reported errors; main drawing thickness fields require actual visual verification, not OCR success alone. Recovery evidence and private workbook paths remain only in the authorized local task directory. Counts describe the observed run, not a later live state.

## FMEA draft, revision 1
Failure mode: batch result cannot serialize / identifier prefix is lost. Effects: lost extraction output, or false row association. Confirmed causes: incomplete temporal type coverage; overly narrow identifier grammar. Prevention: typed date/time handling, incremental record persistence, full identifier boundaries. Detection: final JSON roundtrip/count reconciliation and positive/negative prefixed-code assertions. Action owner: current task implementation; long-term ownership unassigned. Validation: successful rerun and distinct prefixed-code tests. Residual risk: untested workbook variants, ambiguous lot identity and embedded images. S/O/D/RPN unassessed; no scoring criteria supplied.

## FTA draft, revision 1
Top event: reconciliation output unavailable or unsafe to apply. OR branches: output serialization failure (confirmed); incorrect identifier normalization (confirmed pre-delivery); wrong lot/type association (unresolved); unsupported protected source (explicitly held); OCR-only value adopted without visual check (prevented for main reviewed drawings). These branches do not establish incorrect business data in the source.

## QC process chart draft, revision 1
Read-only source capture -> bounded extraction -> per-record recovery write -> aggregate serialization/readback -> identifier and event matching -> evidence review -> proposed update. Gates: hash preserved, count reconciliation, unreadable sources visible, prefix-sensitive identity, distinct issue/inspection/shipment dates, image verification. Escalate unresolved identity or completion evidence to held proposals; never mark source schedules complete from file presence alone.

## Control Plan draft, revision 1
Characteristics: source integrity, temporal serialization, identifier identity, completion semantics. Methods: SHA256 comparison; date/datetime/time serialization and JSON readback; prefixed/unprefixed assertions; field-specific evidence review. Timing: each extraction and before applying any update. Acceptance: unchanged source hash; recoverable serialized records; identifier distinctions preserved; explicit evidence for the exact target event. Reaction: preserve partials, fix only owned tools, rerun with provenance, hold ambiguous writes. Owner: current task; future owner unassigned. Effectiveness: rerun and identity assertions verified; a document update alone is not proof against every workbook variant.

## Sharing boundary and open items
This sanitized card contains no engineering drawings, private raw logs, credentials or workbook contents. Remote knowledge sync is separately receipted. Satellites are unattempted unless fresh identity checks and copy hashes are recorded. Future historic-source imports need a new live inventory; no watcher or automatic restart is registered by this note.
