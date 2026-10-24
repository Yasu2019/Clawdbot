# Search lessons: macro workbook coverage, document AI routing and retrieval verification

Incident: INC-SEARCH-DOCUMENT-SCOPE-XLSM-20261025-01
Observed on K10, 2026-10-25 JST. Historical reviewed knowledge, not live telemetry.

- A supported file extension in discovery must also have a reader and an indexing path. Existing completed directories need explicit backfill after adding an extension; changing the allowlist alone does not repair historical omissions.
- Filename catalog counts do not prove body coverage. Distinguish metadata-only, extracted, encrypted, encoding-review, image/OCR and unsupported states.
- Read spreadsheet OOXML and VBA statically with bounded expansion. Honor the declared VBA codepage with strict decoding. Never run macros, formulas or external links just to index. Verify original file identity and read-time stability.
- Route AI-generated conditions to the selected domain. An AI panel nested inside mail controls and a mail-only apply handler cannot serve document search. Preserve follow-up clues, invalidate stale responses after scope/input/model changes, and send query intent only, not document bodies.
- Small local models may invent title-only or phrase restrictions. Keep explicit user constraints, reject unsupported filters, and verify actual retrieval. A valid JSON answer is not evidence of search accuracy.
- An OR fallback over a multi-GiB FTS content table can time out before matching. Drive candidates from MATCH and preserve unnormalized rows through a compact read-only FTS5 docsize ID anti-join. Verify both positive and negative cases; do not silently drop pending rows.
- Record model, observation time, condition-generation latency, retrieval latency and reference-case limits. A few successful examples do not establish general precision or recall.
- Preserve unrelated jobs. Restart only the verified target search application when deploying; refresh listener identity and independently check ingestion processes afterward.
- At full host CPU load, the below-normal interactive process responded very slowly. Set only the verified search request process to Normal. In 64-bit ctypes, pass the pseudo-handle as `c_void_p(-1)` and check the return value: the untyped GetCurrentProcess/SetPriorityClass combination returned error 6 and silently left priority unchanged. This was reproduced in a disposable local probe; explicit HANDLE fixed it. Do not change unrelated solver priorities.
- Show a dedicated search-status panel: phase, elapsed time, visible result count and last server-response time. A browser heartbeat proves the page is updating, not that the server has answered. Support bounded request waits and client-side cancellation without terminating ingestion or model jobs.
- Keep expensive statistics out of the interactive request process, bound each collection, and distinguish pending counts from zero. A newly created statistics helper held a blocking catalog lock during diagnosis; stopping only that owned read-only helper immediately restored the query. The exact low-level lock mechanism remains unresolved; do not blame unrelated jobs.
- A time-limited page must advance at least one candidate if its SQL query itself consumes the page budget. Otherwise the same cursor can repeat forever.
- Knowledge synchronization requires destination-specific read-back/hash evidence. Local files and pending queues are not cloud completion. Keep bounded deduplicated retries for unavailable destinations; do not publish unrelated dirty worktree changes.

Controls: unscored draft FMEA, FTA, QC process chart and Control Plan are linked to the same incident in the canonical project knowledge folder. Related regressions cover Japanese XML/VBA text, unchanged originals, Drive/multi-scope apply, follow-up history, stale-response rejection, unnormalized-row rescue and real catalog retrieval.

No credentials, raw mail, customer documents, signed URLs or private engineering workbook content are included in this card.
