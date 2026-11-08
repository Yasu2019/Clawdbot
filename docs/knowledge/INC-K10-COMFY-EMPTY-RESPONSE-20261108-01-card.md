# INC-K10-COMFY-EMPTY-RESPONSE-20261108-01

Observed 2026-11-08 09:07–09:08 JST on NucBox_K10. Current task orca-local-zl8h, related memory-pressure incident INC-K10-FLUX-DYNAMIC-RAM-PRESSURE-20261108-01. Source: owned worker traceback, successful ComfyUI history and live endpoint regression check.

## Facts / cause / impact

FLUX prompt50ff0280-ac4f-434b-bb1e-7be153e9eaf3 completed successfully after382.04seconds. A real512x320 PNG247853bytes was saved and visually inspected: alpine lake, golden sunrise, mountains and red/gold sailboat. The worker then called /free to reset its completed-stage caches. That endpoint returned successful empty content, while the API helper always called json.load(response). Confirmed root cause: application assumed every successful HTTP response had a JSON body. The worker raised JSONDecodeError and stopped before submitting the Wan stage. Image generation did not fail.

## Implemented correction / verification

Preserved the prior script/status/traceback and the successful workflow/history/PNG on F:. Changed the helper to read bytes and return an empty object for an empty successful response; nonempty bodies still require valid JSON, and HTTP errors are not disguised as success. Actual regression check09:08JST: own8190 queue empty, /free empty success accepted, /system_stats normal JSON decoded. Report api_response_test.json records both positive checks. No existing server/work/job was stopped by this correction.

Added stage reuse only if the saved keyframe history says success, exact expected owned prompt matches and the PNG SHA256 equals its original history output. Resumed from that real artifact rather than blindly regenerating FLUX. Wan start_image prompt675d2614-b89c-4bf3-b233-ea0a19958872 was accepted at09:08JST. Actual MP4 decode and visual acceptance remain pending in this revision. Source/evidence folder F:/clawstack_data/knowledge/flux_demo_20261108. User-facing status is ACTIVE, not COMPLETE. No checkpoint-resume claim for native inference.

## FMEA — INC-K10-COMFY-EMPTY-RESPONSE-20261108-01

Failure mode: successful empty control response treated as invalid JSON. Effect: pipeline stops after valid image, no video. Cause: unconditional JSON decode (confirmed). Prevention/detection: optional empty success handling and actual empty/JSON endpoint checks; preserve normal HTTP failures. Action owner current task agent; long-term owner unassigned. Validation: both endpoint tests passed; exact-artifact stage reuse admitted; full video acceptance pending. S/O/D/RPN unassessed; no invented ratings.

## FTA — INC-K10-COMFY-EMPTY-RESPONSE-20261108-01

Top event: Wan stage not dispatched after valid FLUX output. AND: empty /free success body AND unconditional JSON parsing. Both branches confirmed from traceback and endpoint test. Model, disk and GPU failure are not inferred from this protocol exception. Later inference/encoding failures are separate unresolved possibilities.

## QC process chart — INC-K10-COMFY-EMPTY-RESPONSE-20261108-01

Own queue check → control request → validate HTTP status/body contract → match prior successful stage artifact/hash → dispatch next stage → successful history plus decoded/visually reviewed MP4. Records: test JSON, owned stage histories, canonical incident, Beads link and final receipt. Protocol failure preserves valid prior outputs and records a distinct error, not a model retry.

## Control Plan — INC-K10-COMFY-EMPTY-RESPONSE-20261108-01

Characteristics: HTTP status/body contract and stage artifact provenance. Method: actual empty/JSON endpoint regression check; exact prompt/hash gate. Timing after helper changes and at every stage handoff. Acceptance: empty successful control body allowed, JSON endpoints decode, errors remain errors, next stage uses verified PNG. Reaction: fix verified protocol defect, reuse only validated owned artifacts, retain failure history, finish real artifact validation. Current task agent records test results. These checks prevent this demonstrated failure mode; they do not guarantee all network/model failures are solved.

## Terminal validation — 2026-11-08 09:25 JST

Corrected stage handoff reached successful Wan inference and actual49frame MP4 encoding; the empty-response protocol defect did not recur. A separate visual quality rejection is recorded in INC-K10-VIDEO-VISUAL-GATE-20261108-01-card.md and must not be mislabeled as protocol/model execution success sufficient for delivery. The accepted alternative is an explicitly labeled5second source-preserving camera-motion FLUX demo. A terminal draft used history.prompt[0] queue ordinal as a UUID label; original preserved, future extraction fixed to prompt[1] and final receipt corrected with actual owned UUIDs. Exact source/hash gate already used the correct index, so no unrelated artifact was reused. Actual empty/JSON endpoint tests and completed downstream export validate this protocol correction.
