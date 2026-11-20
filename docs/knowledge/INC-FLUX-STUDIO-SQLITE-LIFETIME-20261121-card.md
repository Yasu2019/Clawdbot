# INC-FLUX-STUDIO-SQLITE-LIFETIME-20261121

Observed 2026-11-21 03:25–03:31 JST on K10, during authorized FLUX Studio video extension (Beads orca-local-gork). Sources: isolated unittest tracebacks, direct local HTTP job/gallery/download queries and decoded MP4. Prior image UI task orca-local-gszg remains historical; no claim its old runtime stayed alive.

## Facts, impact and preservation

Initial video test exceeded its 15-second test deadline while its owned worker was still encoding. Test teardown joined for only five seconds and attempted cleanup with an active writer: Windows WinError32, partial isolated test data removed. Second iteration completed every assertion but cleanup still failed because SQLite handles remained open. Confirmed Python sqlite3 connection context managers commit/rollback but do not close the connection. The added teardown's local connection made that problem deterministic. No production source/model/history was deleted; only newly created isolated test roots were affected. Slow first-iteration execution cause is UNKNOWN; per-frame SQLite reads were observed, but their contribution to elapsed time was not isolated experimentally.

Unrelated robot GPU training native PID40108 / launcher55012 (train_v50_walk_rsl.py, source AtsugiMechaCity) was live at03:21–03:30 JST; external owner not verified. Existing FLUX/Wan finite scheduled watchers and all old outputs preserved. No cleanup of them is proposed. At03:29:17JST the fresh engine guard returned HELD for another GPU job and insufficient host available RAM. No new AI inference/model load dispatched. Both old Comfy endpoints were unavailable, not proof of a host outage.

## Changes and verification

Store.connect now uses an explicit contextmanager with finally db.close(). Tests wait for actual terminal states, join their writer before cleanup and preserve an active test directory rather than deleting it. Camera cancellation checks occur every six frames, with periodic persisted heartbeat and finite120s encode budget. The integration harness uses realistic90s artifact wait and its original image suite is run separately to avoid duplicate inheritance and a future-dated fixture affecting ordering. No assertions on content, provenance or terminal success were weakened.

Later source regression passed9/10 assertions/tests, but the final2-second GPU-wait fixture exposed a deadline/cancel race: cancel_requested=1 was persisted while the worker's timeout exception overwrote the state as FAILED. The source now checks cancellation at the wait deadline and prioritizes cancellation in worker exception handling; ATTENTION is preserved. Video integration wait/run fixtures use30seconds to allow the cancel assertion to exercise waiting under disk load. Final corrected-suite outcome is recorded in the separate QA receipt; an expected malformed-upstream rejection traceback is not itself a failed test. Incident Beads orca-local-fs0k remains open while running-runtime rollout is unverified.

New video support: source-hash-pinned gallery images; explicitly distinct CPU camera motion and Wan2.2 image-to-video; fixed server-side workflows, GPU lease/admission, finite waits, exact owned cancel, persisted jobs, independent finite observer, full MP4 decode/size/fps/frame-count/hash validation, HTTP byte ranges and MP4 download. Decoding is not visual-quality acceptance. Wan's prior visual failure is linked in INC-K10-VIDEO-VISUAL-GATE-20261108-01-card.md.

Real local HTTP camera job f28a02985d074a8aa18264d7a8342509 completed03:29:38JST:512x320,24fps,48 distinct decoded frames,2s,H264,158801bytes,SHA256 d4b3a34ec27a536e96c1bec4dbc832f45a77be6b2f675b5b33bdb57975ef8330. Source FLUX PNG SHA a76227b643d9d73741f6c3eb16f45acc72404d76a4dded4c1e77e36ceb3de74a. Independent observer readback SUCCEEDED03:29:44JST. Visual review and final regression results are recorded separately in apps/flux_studio/QA_20261121.md. Real Wan GPU inference remains NOT_TESTED in this task because admission is HELD. Mocked upstream tests are never described as real Wan inference.

At~03:31 JST automatic approval review rejected stopping/restarting the newly created idle UI process (launcher57544), returning only blocked by policy. No alternate stop mechanism attempted. Current UI remains running with working video extension; the explicit SQLite-close source correction requires a later authorized restart to apply to that already-running process. Isolated regression uses corrected source. This is a runtime rollout limitation, not a completed repair of that running instance.

## FMEA draft

Failure mode: test cleanup races active writer / SQLite handle lifetime relies on garbage collection. Effect: test artifact loss, Windows locked-file errors, potentially accumulated runtime handles. Cause: insufficient teardown join and missing explicit connection close confirmed; execution latency mechanism UNKNOWN. Prevention/detection: explicit close, finite join, retain-live-writer gate, real MP4 and HTTP regressions. Action owner: current task agent; long-term owner unassigned. S/O/D/RPN unassessed. Residual: running UI pending source rollout; real Wan quality and current browser QA not established by unit tests.

## FTA draft

Top event: test artifact cleanup fails or removes data still needed by worker. OR branches: active writer AND premature cleanup (observed first run); live SQLite connection AND attempted Windows removal (observed second run). Slow encoder/storage branch unresolved; no hardware-fault diagnosis. Separate false-video-acceptance branch: valid container AND unreviewed visual output; mitigated by truthful method/quality labels, not a claimed automatic visual-quality test.

## QC process chart draft

Inspect old processes/tasks/queues and data volume identity → preserve unrelated jobs → pin source image hash → admit CPU/GPU independently → create one owned job and observer → require real terminal artifact → decode expected frames/dimensions/fps and verify hash → preview and user visual review → save MP4. For tests: join writer and close DB before cleanup; if still active preserve partials and fail visibly.

## Control Plan draft

Characteristics: source hash, job/prompt ownership, DB connection closure, worker liveness, expected MP4 structure, method/quality labeling. Methods: contextmanager finally-close; bounded worker join; exact-ID cancellation; decode plus HTTP range/download tests; prior visual incident retrieval. Timing: each source use/job/terminal transition/test teardown. Limits: UI offers2/3/5s,24fps,existing512x320/512x512/320x512 images; Wan4n+1 frames; application-specific conservative GPU admission retained (not universal approved limits). Reaction: preserve partials/old jobs, hold GPU dispatch, report ATTENTION/no blind resend, do not bypass approval rejection. Validation: QA note + actual job metadata; updated documentation alone is not repair evidence.

## Knowledge and storage

Source/code and audit on D; video/data/temp/cache on existing verified F volume9b8ab29d-df50-45f4-b8c7-45b2a9e7ed99, Toshiba20141129010180. All three external HDD identities/health/free bytes checked03:21–03:22JST; F~266GB free,G~109GB,H~49GB, healthy/non-read-only. No archive transfer/deletion; existing appropriate F app directory retained with ample reserve. No new C work data/temp/cache intentionally configured. Knowledge destination receipts distinguish saved/verified, failed/pending and unattempted; no satellite rollout claim.
