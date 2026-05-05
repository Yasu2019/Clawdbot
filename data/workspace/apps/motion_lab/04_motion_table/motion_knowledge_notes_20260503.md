# Motion Knowledge Notes

Date: 2026-05-03

## Stored Knowledge

The Mixamo motion know-how is stored in:

- `motion_asset_learning_registry.csv`
- `motion_knowledge.db`
- `mixamo_*_asset_inspection_20260503.json`

## Current Understanding

- The downloaded FBX files are structurally usable in Blender.
- The skeleton is Mixamo standard: `mixamorig:*`.
- Finger bones are present.
- Walking, Idle, Talking, Pointing, and Meeting actions can be treated as a reusable motion dictionary.

## Recommended First Motion Composition

Use a single low-cost diagnostic cut:

1. `Walking.fbx` or `Walker Walk.fbx`
2. `Idle.fbx`
3. `Talking (3).fbx`
4. `Pointing (2).fbx`

## Development Rule

Do not attempt full original human motion from scratch first. Use sample motions as references and compose them with:

- trimmed action ranges
- NLA blending
- upper-body and lower-body separation
- shoulder, elbow, wrist, and hand correction layers
- mouth, blink, head, and facial micro-motion overlays

## Quality Gate

Proceed to MP4 only after seven diagnostic frames pass:

- character identity
- visible motion variation
- mouth motion
- blink or facial micro-motion
- shoulder-to-hand continuity
- no obvious foot sliding
- slide or board content matches narration
