# INC-K10-VIDEO-VISUAL-GATE-20261108-01

Observed 2026-11-08 09:22–09:25 JST on K10. Task orca-local-zl8h; related memory/empty-response incidents dated20261108. User asked for a FLUX demo video; no user requirement for a particular animation engine was given.

## Evidence and acceptance

Wan I2V produced a real H264 MP4,255930bytes,512x320,49frames/24fps/2.0417seconds, SHA2566a8c32123b0b56c26fd03cfe42c8538bbb3d7cf94708d8ce8c3f34d56df43107. All49 decoded frames were distinct. Mechanical checks passed, but the agent's four-frame visual review found large vertical smearing/geometry/lighting distortions in later sky/water frames. That output was rejected for final delivery and retained unchanged as flux_demo.mp4. Exact cause of model quality degradation UNKNOWN; no unverified model/config diagnosis asserted.

Confirmed control gap: the worker labeled COMPLETE and sent a local MP4-verified notice after decode, before visual acceptance. Notice return0 means accepted, not user-read. The manual gate caught the poor output before final chat delivery. Export success, frame count and distinct frames are insufficient artistic/semantic quality criteria.

## Correction and actual delivered variant

Preserved raw worker_terminal_status.json and rejected Wan artifact/history/contact sheet. Future worker phase changed to ARTIFACT_DECODED_PENDING_VISUAL_REVIEW; notification now states visual acceptance still required. Corrected future history UUID extraction: prompt[1] is UUID; prompt[0] is queue ordinal. Exact UUID/hash stage reuse already used prompt[1], so the mislabeled terminal draft did not change the input image. Original draft preserved; final receipt contains correct IDs and a timestamped correction.

Created a separate source-faithful camera pan/zoom variant from the actual FLUX Schnell image, rather than calling the rejected Wan output acceptable. Method is explicitly deterministic eased pan and1.12x zoom; no model-generated subject/water movement is claimed. Final flux_panzoom_demo.mp4:339023bytes,H264,512x320,120frames/24fps/5seconds, SHA25664794d9a2023245a72d6a43314b4cd9819b22def9f29d7f01b450b940d684eb3. All120frames decoded and were distinct. Four-frame visual review passed: scene geometry, boat and water remain coherent, only camera framing changes. FLUX source SHA256a76227b643d9d73741f6c3eb16f45acc72404d76a4dded4c1e77e36ceb3de74a; prompt50ff0280-ac4f-434b-bb1e-7be153e9eaf3. Final verification JSON records method and rejected alternative explicitly. User was offered camera-motion versus regenerated scene-motion preference; no answer was received while the clean variant was independently prepared. Broad FLUX demo delivery is labeled by its actual method; subject-motion quality remains unaccepted.

At09:24:52JST own8190 queue0/0 checked and completed-stage caches freed. Only current finite watcher FLUX_Demo_FiniteWatcher_20261108 disabled after acceptance; older watchers/jobs untouched. Final clean-variant msg accepted return0, not read acknowledgment. Existing8188 not stopped. Files: F:/clawstack_data/knowledge/flux_demo_20261108.

## FMEA — INC-K10-VIDEO-VISUAL-GATE-20261108-01

Mode: structured artifact success mistaken for usable video. Effect: misleading readiness/poor-quality delivery near miss. Confirmed cause: COMPLETE/notice before visual gate; degradation cause UNKNOWN. Controls: explicit decoded-pending-review state, decoded metadata and visual scene review, truthful method labels and retention of rejected attempts. Owner current task agent; long-term owner unassigned. Validation: actual poor clip rejected; clean variant decoded and reviewed. S/O/D/RPN unassessed; native scene-motion quality remains an open item.

## FTA — INC-K10-VIDEO-VISUAL-GATE-20261108-01

Top event: unusable video falsely accepted. AND: mechanically valid but visually poor clip AND missing/late visual acceptance. First branch observed; manual review prevented final chat delivery. Premature local machine notice is confirmed, user reading unknown. Encoding/container failure is not the cause of the observed visual distortion.

## QC process chart — INC-K10-VIDEO-VISUAL-GATE-20261108-01

Generate → decode dimensions/frame count → inspect representative frames and motion/source fidelity → accept only requested usable artifact with true method label → final notice/delivery. On rejection preserve raw output, apply a reviewed improvement or explicitly labeled alternative within scope, then reverify. Final artifact and experimental alternative must not share an ambiguous acceptance label.

## Control Plan — INC-K10-VIDEO-VISUAL-GATE-20261108-01

Characteristics: actual usability, scene consistency, motion provenance and status truthfulness. Method: successful full decode plus agent visual review and source/history/hash correlation. Timing before final readiness notice or task closure. Acceptance: intended dimensions/duration and coherent image geometry; no invented universal aesthetic score. Reaction: do not deliver a rejected artifact as finished; retain evidence, improve and verify, report unresolved native-motion limitation. Current case validated these gates; documentation alone is not the improvement.
