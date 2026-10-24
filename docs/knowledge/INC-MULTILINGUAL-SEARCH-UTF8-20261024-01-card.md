# Knowledge card: multilingual research query integrity

## Failure pattern

An academic metadata API can return HTTP-successful records for a query whose non-Latin text was corrupted by an encoding error. A nonzero result count and zero API errors do not demonstrate that the intended language or topic was searched.

## Prevention

- Keep query source text in a declared UTF-8 encoding; Unicode escapes are a safe source representation when editor or shell encoding is uncertain.
- Validate expected script markers and reject replacement or mojibake characters before network access.
- Persist the exact query string and language tag with every returned record.
- Parse every snapshot and compare its stored queries with the validated source list before accepting it.
- Record API rows as discovery leads only. Verify original source language, relevance, reuse rights, actual files/fields, material grade, and solver applicability before curation or calibration.

## Recovery

Preserve affected snapshots for audit, mark them invalid for research/curation, correct the literals, and verify both a positive valid-query check and a negative corrupted-query check. Validate effectiveness on the next scheduled pass; do not infer success from task exit code alone.

## Evidence boundary

This card records a 2026-10-24 query-encoding failure and a local script guard. The first corrected scheduled run remained pending at the time this card was written. No dataset calibration or solver change is implied.
