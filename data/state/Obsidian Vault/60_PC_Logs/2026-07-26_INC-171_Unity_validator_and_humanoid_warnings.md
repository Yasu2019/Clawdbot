# INC-171 Unity validator and Humanoid warning gate

## QC facts

The manifest correction passed: zero compile errors, 715 assets imported,
controller and prefab generated, Unity exit 0. The additional validator failed
because `animationImportWarnings` and `animationImportErrors` are not public
ModelImporter APIs in Unity 6000.0.

FBX meta facts: `clipAnimations: []`; translation DOF disabled; automatic mapping
maps `Chest` as human `Spine`; animated `Spine`, `Neck`, `Shoulder.L`, and
`Shoulder.R` are intermediate unmapped bones and their rotations are discarded.

## 5 Why / Fishbone

The validator failed because serialized field names were mistaken for public
properties. Loop configuration failed to persist because it ran in
OnPreprocessModel instead of OnPreprocessAnimation. Retarget warnings arise from
automatic bone mapping rather than the source animation data.

## FMEA

| Mode | S | O | D | RPN | Action |
|---|---:|---:|---:|---:|---|
| Private API assumption | 4 | 4 | 2 | 32 | Documented API only |
| Loop settings absent | 7 | 6 | 4 | 168 | OnPreprocessAnimation |
| Bone rotation discarded | 8 | 7 | 3 | 168 | Explicit mapping |
| Translation DOF off | 6 | 6 | 3 | 108 | Enable DOF |

## Countermeasure / rollback

Remove four invalid validator references; parse warning/error meta separately;
move clip setup to OnPreprocessAnimation; explicitly map spine/chest/neck/
shoulders and limbs; enable translation DOF; force reimport; require clean meta,
valid Human Avatar, correct loops, states, parameters, prefab components, and
Unity exit 0.

Rollback uses manifest backup `manifest.json.bak_20260726_214511`,
ProjectVersion backup `ProjectVersion.txt.bak_20260726_205720`, and deletion of
the newly added validator plus meta.

## Final verification (2026-07-27)

- Unity exit 0; validation PASS after AssetDatabase cleanup.
- Avatar Human and Valid.
- Idle 8.333 s loop, Talking 5.000 s non-loop, Walking 1.367 s loop.
- Three custom clips; translation DOF enabled.
- Nineteen mappings, including Spine/Chest/Neck/shoulders.
- FBX serialized errors and warnings empty.
- Controller states Idle/Talking/Walking and parameters Speed/IsTalking valid.
- Prefab controller assignment, root-motion off, and motion component valid.

The existing FBX required explicit synchronous force reimport. A script change
alone did not update its meta. The first backup move command had a parse-only
parenthesis typo and made no file changes; the simplified exact-path retry moved
the backup and meta outside Assets.
