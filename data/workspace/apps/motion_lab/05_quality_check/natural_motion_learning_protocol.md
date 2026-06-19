# Natural Motion Learning Protocol

Date: 2026-05-03

## Purpose

Build a reusable experience base for IATF character animation so each render attempt improves the next one instead of starting from scratch.

## Required Loop

1. Convert the script segment into motion tags.
2. Pick candidate mocap clips from the asset registry.
3. Run retarget dry-run and record armature/bone names.
4. Render seven diagnostic frames before MP4 output.
5. Score the result and update the registry.
6. Only compose MP4 after identity, motion, mouth, blink, and slide-content checks pass.

## Robotics Gait Gate

For walking or mecha locomotion cuts, run the robotics-informed gait gate before final MP4 composition.

Inputs should come from Blender/render QA metrics when available:

- stance foot world velocity
- foot ground penetration
- projected CoM/support margin
- root speed variation
- swing foot clearance
- maximum hip/knee/ankle angle delta per frame
- lateral CoM sway ratio

Use:

`data/workspace/apps/motion_lab/05_quality_check/robotics_gait_motion_algorithm.py`

Knowledge DB:

`data/workspace/apps/motion_lab/assets/web_sourced/robotics_gait_knowledge/robotics_gait_knowledge.db`

The gate is observation-first. It reports PASS/REVIEW/FAIL and correction suggestions; it must not destructively rewrite animation data without an explicit later implementation step.

## Quality Score

Use `0` to `5`.

- `0`: unusable, broken rig or no visible motion
- `1`: visible motion but severe distortion
- `2`: partial use, needs camera hiding or manual cleanup
- `3`: acceptable preview quality
- `4`: usable for IATF instructional video
- `5`: reusable master clip for future scenes

## Pass Criteria

- Character identity is correct.
- The sample frames are not nearly identical.
- Shoulder, upper arm, forearm, wrist, and hand rotations look connected.
- Mouth movement is visible during narration.
- Blink or facial micro-motion appears at least once in the cut.
- Foot sliding is not visible in the selected camera angle.
- Hands do not visibly penetrate the body or slide content.
- Camera framing hides weak contact points when needed.
- Slide or board content matches the narration intent.

## Experience Record

For every candidate clip, update:

- source and license status
- local path
- tags
- intended IATF use
- quality score
- known issues
- next action

The main registry is:

`data/workspace/apps/motion_lab/04_motion_table/motion_asset_learning_registry.csv`

## User-Download Requests

When a library requires login or manual download, ask the user for specific clip names and formats. Prefer:

- FBX
- Mixamo or HIK skeleton when available
- no character skin if the site offers animation-only export
- in-place motion for gestures and talking
- root-motion walk only when the scene requires actual travel

## First Download Priority

1. Calm walk cycle
2. Idle breathing or idle talking
3. Talking hand gesture
4. Pointing or presenting gesture
5. Subtle reaction or thinking gesture

Avoid acrobatic, dance, fight, exaggerated anime, or fast locomotion motions for IATF training unless a specific cut needs them.
