# Atsugi Terrain Grounding Generic Quality Playbook

Date: 2026-05-16 JST

## Purpose

Make the Atsugi terrain/building grounding lessons reusable for future 3D maps so the first diagnostic render is much closer to acceptable quality.

## Can This Be Generalized?

Yes, but not as a one-click guarantee for every source map. It can be generalized as an intake and validation pipeline:

1. Detect and record source coordinate axes.
2. Avoid naive bounding-box scaling unless explicitly validated.
3. Score horizontal terrain/building overlap across candidate offsets.
4. Raycast or nearest-sample terrain under every building footprint.
5. Use footprint terrain range, not only center height, to place buildings.
6. Add foundations or pads for sloped terrain when a flat building footprint would visibly float.
7. Render close and wide diagnostic screenshots.
8. Require visual review before declaring the map usable.

## Past Trouble DB Entry

Problem:

- Buildings appeared floating above the Atsugi terrain after an apparently successful numeric alignment.

Trigger:

- User manually inspected the generated image and found visual floating.

Reproducible condition:

- Building footprints on slopes or uneven terrain.
- Center-point terrain height is used as the only Z reference.

Corrective pattern:

- Sample each building footprint on a grid.
- Use the highest sampled terrain point minus a small embed depth for the building bottom.
- Add a foundation/pad down to the lowest sampled terrain point when the footprint terrain range is non-trivial.

Current Atsugi values:

- Footprint grid: 5 x 5
- `BUILDING_EMBED_DEPTH = 0.35`
- `BUILDING_FOUNDATION_ENABLED = True`
- `BUILDING_FOUNDATION_MARGIN = 0.35`
- Adjusted buildings: 394
- Telegram corrected images: `4616`, `4617`
- Backup commit: `e0e2a09`

## FMEA

| Failure Mode | Effect | Cause | Current Control | Recommended Control |
| --- | --- | --- | --- | --- |
| Naive bbox terrain scaling | Terrain and buildings separate or distort | Different origins and axis conventions | Web-viewer-like no-scale alignment | Require axis/bbox audit before render |
| Center-only building grounding | Corners or low-side edges float | Sloped terrain under flat footprint | 5 x 5 footprint sampling | Store footprint range and block high-risk cases |
| Terrain/building XY mismatch | Buildings snap to wrong terrain patch | Export origin mismatch | Best building-overlap offset scoring | Preserve top candidate list and thresholds |
| Visual pass assumed from metrics | Floating missed until user review | No screenshot acceptance gate | Manual close/wide visual review | Add automated screenshot checklist or pixel/edge QA |
| Large raw terrain mesh blocks browser path | WebGL load failure or long latency | 100MB+ OBJ/FBX inputs | Blender offline diagnostic baseline | Add simplification/export stage after geometry is trusted |

## FTA

Top event:

- Future downloaded 3D map fails first visual quality because buildings or models float.

Contributing branches:

- Coordinate branch: wrong axis mapping, wrong origin, bbox scaling used too early.
- Sampling branch: only center raycast, no footprint corner/edge sampling.
- Terrain branch: faceted/raw terrain, slope under flat buildings, local ditches or roads.
- Review branch: no close/wide render, no human visual gate, no Telegram/image handoff review.
- Export branch: browser path tested before offline geometry quality is stable.

Minimal prevention set:

- Axis audit + overlap scoring + footprint sampling + foundation/pad handling + close/wide screenshot review.

## 5Why Summary

Why did buildings float?

- They were placed by center terrain height, not by full footprint contact.

Why was that insufficient?

- Terrain height varies across large/sloped building footprints.

Why did metrics not catch it?

- Raycast hit distance can be perfect while low-side visual gaps remain.

Why was it not caught earlier?

- The review relied on generated images existing, not on deliberate close/wide visual inspection criteria.

Why could it repeat on other maps?

- The generic intake did not yet require footprint sampling and screenshot acceptance gates.

## Generic First-Run Acceptance Checklist

- Building/terrain overlap score recorded.
- All candidate buildings have terrain hit or explicit skip reason.
- Footprint terrain min/max/range recorded.
- Any building with high terrain range has foundation, pad, or explicit review flag.
- Close and wide images generated.
- Human or automated visual check confirms no obvious floating.
- Large `.blend` files are kept local unless Git LFS is intentionally enabled.

## No-Go Conditions

- Building count is high but adjusted count is low without clear skip reasons.
- Mean terrain/building overlap distance is high.
- Center raycast succeeds but footprint range is unmeasured.
- Close/wide screenshots are not opened before sending or declaring success.
- Terrain is modified destructively before a backup and review.
