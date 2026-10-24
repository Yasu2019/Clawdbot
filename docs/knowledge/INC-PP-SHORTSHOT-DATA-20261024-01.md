# Incident orca-local-xpb: PP short-shot dataset field correction

- Observed: 2026-10-24 14:29:03 +0900 (Asia/Tokyo)
- Source: K10 workspace `D:\Clawdbot_Docker_20260119`; local curated dataset and its README; primary publication [Chien et al. 2024](https://www.mdpi.com/2073-4360/16/20/2874), DOI 10.3390/polym16202874.
- Data identity: 8 curated PP short-shot/flow-imbalance conditions; source article PDF SHA-256 `9C863EAA807D54453CA0F8AFF9D9937CA4225D4594F960A1A524458F5E869F7C`.
- Impact: four MIM records in `pp_shortshot_flow_length_deviations.csv` represented blank/unreported packing pressure as `0`. A future join could falsely match a solver condition at zero packing pressure. No solver results were compared using this field during this work; impact is a potential false comparison, not a demonstrated solver error.
- Evidence: dataset README says the article's MIM packing-pressure cell is blank and must not be inferred; CSV had `0` in MIM rows. Curated source notes report N2 0.4 wt% for MIM.
- Root cause: UNKNOWN; the precise extraction/transcription step that changed blank to zero was unavailable.
- Prior/related work: research parent Bead `orca-local-9qx`; original source PDF and dataset remain in their existing paths. No other job/task was stopped, overwritten, or reused.

## Actions and verification

- Corrected all four MIM `packing_pressure_bar` entries to empty (unknown), leaving CIM's reported 600 bar entries intact.
- Added `blowing_agent_N2_wt_pct` to keep the reported 0.4 wt% MIM condition separate from packing pressure. CIM is empty for this variable.
- New curated CSV SHA-256: `0fbe0b7b08f7f680f2d0b04bfa53bf334ab9f301d2069d97c0bf0be29ffa4788`.
- Added `compare_chien_pp_shortshot_imbalance.py`; it pins the hash and rejects missingness mismatches (including replacing MIM unknown pressure with zero).
- Four focused tests pass: zero-error fixture, null-vs-zero preservation, wrong gate-area rejection, and condition checks. These validate the adapter, not OpenFOAM physics or a solver run.
- Added the source correction to dataset README and scope/usage to validation README. No calculation was dispatched.

## FMEA draft (S/O/D and RPN unassessed)

- Failure mode: unreported process input transcribed as numeric zero.
- Effect: false condition match and invalid short-shot error metric, leading to misleading solver assessment.
- Cause: UNKNOWN; only the inconsistency is confirmed.
- Prevention/detection: preserve blank as null; pin source hash; check process-specific null/value invariants; require matched condition keys.
- Owner: unassigned. Validation: four adapter tests pass. Residual risk: other curated datasets may have similar issues and were not audited here.

## FTA draft

Top event: invalid solver-vs-experiment comparison due to false process-condition match.

- A: missing source setting represented as a number ? **confirmed for four MIM cells; corrected**.
- B: comparator accepts mismatched input ? guard added and tested for this adapter.
- C: other numeric condition/unit transcription error ? open, not assessed.
- D: geometry/material/response-definition mismatch ? open; a future case still requires independent matching.

Only branch A is confirmed.

## QC process chart draft

- Step: curate Table 2 into derived CSV.
- Gate/method: compare against source extraction notes; retain unknowns as blank; check hash, unique IDs, and process-specific field invariants.
- Criteria: MIM packing pressure null; MIM N2 0.4 wt%; CIM packing pressure retained as reported; pinned hash matches.
- Record: this note, corrected CSV, test results.
- Escalation: stop scoring and record a data-quality issue if source and curated fields disagree.

## Control Plan draft

- Characteristic: MIM packing pressure and N2 setting.
- Method/frequency: pre-score checks on every invocation of the comparator.
- Acceptance: MIM packing remains null; N2 equals 0.4 wt%; all listed numeric/text condition fields match within explicit tolerance.
- Reaction: reject input; do not impute or score.
- Owner: unassigned; no formal authority/limit was specified.
- Effectiveness: tested for this dataset adapter only; broader curation effectiveness remains unverified.


## Knowledge synchronization status (updated 2026-10-24 14:33 JST)

An authorized ByteRover attempt returned CLI exit 0 but stdout reported all four API retries exhausted with `ECONNREFUSED 127.0.0.1:11434`; the then-current wrapper misreported `curated`. No remote write is verified. Related wrapper incident `orca-local-1w8` fixes expired-session and failure-text classification with six passing tests. This PP data card is now `queued_locally` in `D:/Clawdbot_Docker_20260125/data/workspace/byterover_curate_queue.jsonl`; remote sync remains pending. The curated read-only K10 Filesystem MCP snapshot export is independently verified by matching source/export SHA-256.
