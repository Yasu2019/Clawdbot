# OpenClaw Blender Motion Complete V1 - Integration Notes

Date: 2026-05-03

## Decision

ADOPT_PARTIAL.

The ZIP was staged under:

`data/workspace/apps/motion_lab/_incoming/openclaw_blender_motion_complete_v1`

It must not be copied over the existing Motion Lab or IATF video factory directly. The package overlaps with the current `motion_lab` workflow, but it adds useful, focused material for the current IATF character-motion issue:

- script-to-motion-tag decomposition
- Mixamo/BVH/Rokoko/VRM motion-source policy
- retarget dry-run helper
- hand/foot candidate discovery
- visual quality checklist for foot sliding, hand penetration, eye line, timing, and camera composition

## Why Not Full Adoption

The existing repository already has a Motion Lab hub and IATF video pipeline. Adding this ZIP as a separate app would duplicate documentation, portal cards, and workflow ownership.

## Immediate IATF Use

Use the staged ZIP as a reference for the next IATF video PDCA loop:

1. Convert the script segment to motion tags before Blender animation.
2. Prefer existing or external mocap clips for walk, gesture, explain, and reaction motions.
3. Run a dry-run armature/bone report before applying retarget changes.
4. Check seven diagnostic frames before MP4 output.
5. Treat shoulder, upper arm, forearm, wrist, and hand continuity as a required pass/fail item.

## Candidate Files

- `_incoming/openclaw_blender_motion_complete_v1/scripts/tools/script_to_motion_tags.py`
- `_incoming/openclaw_blender_motion_complete_v1/scripts/blender/retarget_helper.py`
- `_incoming/openclaw_blender_motion_complete_v1/scripts/blender/motion_quality_checker.py`
- `_incoming/openclaw_blender_motion_complete_v1/configs/motion_source_policy.yaml`
- `_incoming/openclaw_blender_motion_complete_v1/docs/04_quality_check.md`

## No-Go Conditions

- Do not overwrite existing `motion_lab` docs or scripts without a reviewed diff.
- Do not modify Blender, Docker, Rails, or LiteLLM configuration for this import.
- Do not auto-download Mixamo/BVH/Rokoko assets without license and cost confirmation.
- Do not proceed to MP4 if diagnostic frames fail character identity, arm continuity, lip sync, blink, or slide-content checks.
