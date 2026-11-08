# INC-K10-FLUX-DYNAMIC-RAM-PRESSURE-20261108-01

Observed 2026-11-08 08:50–09:01 JST on NucBox_K10; sources: live ComfyUI API/owned histories, nvidia-smi, Win32 OS/pagefile queries and exact process identity. Related rule: RULE-OBJECTIVE-FOLLOWTHROUGH-20261103; current video task orca-local-zl8h.

## Facts and impact

User requested a FLUX-origin demo video. A completed earlier Wan-only clip was preserved, not substituted. Current pipeline: FLUX Schnell FP8 keyframe512x320/4steps then Wan2.2 TI2V49frames24fps/16steps. Both existing server queues8188/8190 were empty; no external GPU Python training appeared in the live compute list. The task's idle8190 model caches were freed, leaving373MiB used/15,678MiB free GPU at08:52JST. Host14physical/20logical, DIMMs16+32GiB, OS50,095,444KiB visible and11,762,344KiB available. Host logical aggregate CPU samples08:51:11/12/13JST0/12/15percent; not solver-thread saturation or live guest allocation.

Attempt1 used existing dynamic VRAM/default pinning behavior. During initial FLUX sampling, dedicated server PID28084 private bytes rose from~1.16GB to20.02GB. Host available RAM fell to456,588KiB at08:57:48, while C: free fell from7,373,463,552bytes at08:50 to~266MB. Model progress remained0/4 while initializing; no image had been generated. The temporal association with this run is verified; exact cause of C: growth is UNKNOWN because no pre-run pagefile allocation baseline was captured. At08:58:57 Win32_PageFileUsage reported C:/pagefile.sys allocation38,167MB/current3,596MB/peak9,419MB and D allocation16,448MB/current3,496MB/peak9,226MB. Do not equate saved peak with current use or assert an exclusive root cause.

## Containment and improvement

Confirmed running queue matched only owned prompt9aed5203-4774-4991-b26d-81f9ec8e6c97. Sent targeted /interrupt at08:57:13. History records execution_interrupted in KSampler; queue0/0 confirmed08:57:36. This is fresh seeded inference, not a solver-native resumable checkpoint. Saved the complete first workflow/history/status/script as attempt1 files on F:. /free reset idle caches. No unrelated job/checkpoint deleted or stopped; no Windows/WSL reboot, pagefile edits or security changes.

Dedicated8190 still retained~5.7GB private memory after the interruption. Its exact PID/main.py/port8190 command and empty queue were verified, then only that current-task video server was terminated after inference ended and restarted. Existing8188 was left healthy and its queue untouched. New server launcher56108/native PID3380 uses --fast-disk --disable-pinned-memory with original1.5GiB reserve; output/temp/user/database on F:, custom nodes disabled. These are per-task experimental settings, not a fleet-wide policy change. Source supports preferring disk-backed dynamic loading and disabling fixed RAM registration. Hypothesis: reducing RAM-pinned staging prevents this peak; validation still pending full sample completion. At09:01:18 new run had~6.02GB process private memory, OS6,526,148KiB available and C:253,308,928bytes free; no claim that C: capacity was restored.

Second prompt50ff0280-ac4f-434b-bb1e-7be153e9eaf3 is the same seed/settings under a materially changed loading strategy, not an unsupported blind retry. Owned process48940 and independent finite2h task FLUX_Demo_FiniteWatcher_20261108 track it. Terminal notice accepted is not user-read acknowledgment. All partials, histories and logs are in F:/clawstack_data/knowledge/flux_demo_20261108. Actual FLUX PNG/MP4/visual acceptance is not achieved in this revision.

## FMEA draft

Failure mode: memory-intensive model initialization pressures system RAM/disk. Effects: sample interrupted, C: near-full. Confirmed contributing gap: no measured case-specific peak budget before first full checkpoint load; source-level pinning/staging is a suspected mechanism, not established root cause. Controls: native host/OS/guest evidence distinguished, current-job memory/disk observations, targeted own-job interruption, disk-backed/no-pin trial, artifact gates. Owner current task agent, long-term owner unassigned. S/O/D/RPN unassessed. Residual risk: other host work and persistent pagefile allocation; no unsafe cleanups authorized.

## FTA draft

Top event: FLUX demo interrupted before image/video. Observed conjunction: model initialization resource growth AND low host RAM/C: capacity. Branches: RAM pinning/staging hypothesis; pre-existing host consumers observed but not altered; C: growth mechanism unresolved. No claim of broken GPU, corrupted model or host offline. A successful changed-setting trial would support this specific improvement, not prove every branch.

## QC process chart draft

Live process/queue/disk/RAM inspection → model-load budget review → one owned prompt → monitor actual bytes/queue/OS resources → targeted containment when required → preserve full failure evidence → change a relevant setting → rerun from validated seed → verify PNG, conditioned Wan MP4, decode frames and visual contact sheet. Never replace this chain with exit0 or supervisor-start evidence.

## Control Plan draft

Characteristics: actual host available RAM, process private memory, C:/F: free bytes, owned prompt identity, expected outputs. Methods: direct Win32/nvidia/ComfyUI API and decoded video. Timing before dispatch, during initialization and at terminal transitions. Acceptance: specific workflow dimensions/frame count/hash plus visual review; no invented universal memory limit or risk rating. Reaction: preserve other work; interrupt only verified current prompt, no deletion/reboot; use evidenced loading improvement and validate. Actual current trial effectiveness and knowledge synchronization are tracked separately.

## Native/guest evidence follow-up 2026-11-08 09:02 JST
Only docker-desktop was listed as a running WSL distro by direct wsl --list --running. Direct guest nproc20; /proc/meminfo MemTotal32865428kB, MemAvailable22467600kB, SwapTotal8388608kB, SwapFree7613536kB. These are guest observations and were not added to host available RAM. No WSL shutdown/reallocation performed. Probe receipt F:/clawstack_data/knowledge/flux_demo_20261108/live_wsl_observation.json.
At09:02:50JST second attempt private bytes11867779072, host available6309776KiB and C free248594432bytes. First-attempt worst observed private bytes20017422336 and host available456588KiB. This is an observed reduction, not proof that initializations or all later stages succeed; actual PNG/video acceptance still pending.

## Validation revision — 2026-11-08 09:08 JST

Changed-loading trial produced a real512x320 FLUX PNG in382.04seconds; successful prompt50ff0280-ac4f-434b-bb1e-7be153e9eaf3 and source/artifact SHA equality verified. The image was visually reviewed (lake, sunrise, mountains, sailboat). Around completion, host available RAM6137956KiB and C free258207744bytes. The case-specific loading improvement therefore passed actual keyframe generation with no repeat of the first trial's observed severe RAM drop; this supports the correction, not an exclusive root-cause proof for all C: growth.

A separate post-image control API parsing defect stopped the pipeline; see INC-K10-COMFY-EMPTY-RESPONSE-20261108-01-card.md for its confirmed cause, FMEA/FTA/QC/Control Plan and actual regression test. Valid image preserved and reused by prompt/hash gate; no duplicate keyframe inference. Wan stage675d2614-b89c-4bf3-b233-ea0a19958872 accepted09:08JST. Full MP4/visual pipeline acceptance still pending.

## Terminal validation — 2026-11-08 09:25 JST

Memory-improved trial completed FLUX and Wan inference/encoding; host available RAM stayed about3–6GiB during the later native generation with C:~250MB, without repeating attempt1's observed sub-0.5GiB RAM drop. C: capacity is not restored; its growth cause remains unresolved. Wan video passed decode but failed visual quality, so it is NOT an accepted native-motion result. See INC-K10-VIDEO-VISUAL-GATE-20261108-01-card.md. A separately labeled FLUX-image camera pan/zoom demo passed full decode and visual review; no misleading native-FLUX-video claim. Source-preserving accepted5second file/hash and rejected attempt are recorded in final_verification.json. The loading mitigation is validated for this case; this does not prove universal system health or solve C: storage management.
