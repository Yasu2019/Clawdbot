# Unity validator API mismatch and Humanoid import warnings (2026-07-26)

## Impact and facts

The approved Physics/Video manifest correction succeeded. Unity compiled with
zero project errors, imported 715 assets, generated the commercial heroine
Animator controller and prefab, logged the importer success message, and exited
0.

An additional commercial-quality validator then failed to compile because it
referenced `ModelImporter.animationImportWarnings` and
`ModelImporter.animationImportErrors`, which are not public Unity 6000.0 APIs.
The generated FBX meta also records retargeting warnings and an empty
`clipAnimations` array. The primary generated assets remain intact.

## Root cause analysis

### 5 Whys

1. The validator did not run because its C# compilation returned 1.
2. Compilation failed because two assumed ModelImporter properties do not exist.
3. The validator was based on serialized meta field names rather than verified
   public API members.
4. The public API documentation lists `clipAnimations` and `humanDescription`,
   but not animation warning/error properties.
5. Warning inspection therefore must remain a separate read-only meta gate.

Separately, loop settings were not persisted because the importer populated
clips in `OnPreprocessModel`. Unity documents that `clipAnimations` is empty on
first import and should be populated in `OnPreprocessAnimation`.

Humanoid warnings occur because automatic mapping maps bone `Chest` to human
`Spine`, leaving the actual `Spine`, `Neck`, and both shoulder bones as
intermediate unmapped transforms. Their animation is discarded. Translation
DOF is also disabled despite Unity's import warning recommending it.

## FMEA

| Failure mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Validator assumes private API | 4 | 4 | 2 | 32 | Use only documented API; meta gate separately |
| Loop settings not persisted | 7 | 6 | 4 | 168 | Configure clips in OnPreprocessAnimation |
| Spine/neck/shoulder motion discarded | 8 | 7 | 3 | 168 | Explicit Humanoid bone mapping |
| Translation DOF disabled | 6 | 6 | 3 | 108 | Enable in HumanDescription |

## Proposed countermeasure

1. Remove only the four invalid warning/error API usages from the validator.
2. Move clip population/loop configuration to `OnPreprocessAnimation`, as the
   official Unity 6000 API instructs.
3. Define explicit Humanoid mapping for Spine, Chest, Neck, left/right shoulders,
   and the already mapped limb bones; enable translation DOF.
4. Force FBX reimport, rebuild controller/prefab, and run the validator.
5. Independently require the serialized FBX meta to contain no import errors or
   warnings, three custom clips, and the expected mapping.

Decision rule: IF Unity serializes a value but does not document a public C# API
for it, THEN validate it outside Unity through the serialized meta file rather
than inventing an API member. IF first-import clips need custom settings, THEN
set them in `OnPreprocessAnimation`.

## Verification / rollback / scope

Current state is fail-closed at the extra quality validator. Primary import
artifacts exist and the approved manifest fix passed. Rollback:

- manifest: `manifest.json.bak_20260726_214511`
- ProjectVersion: `ProjectVersion.txt.bak_20260726_205720`
- new validator: delete the new C# plus generated `.meta`

The correction was executed on 2026-07-27. The FBX was explicitly reimported
with `ForceUpdate | ForceSynchronousImport`; relying on a postprocessor script
change alone did not reimport the existing FBX. The final result is:

- Unity compile and executeMethod exit 0.
- Avatar `isHuman=True`, `isValid=True`.
- Three custom clips: Idle 8.333 s looping, Talking 5.000 s non-looping,
  Walking 1.367 s looping.
- Translation DOF enabled.
- 19 explicit Humanoid mappings, including Spine, Chest, Neck, and shoulders.
- Serialized import errors and warnings both empty.
- Controller states Idle/Talking/Walking and parameters Speed/IsTalking valid.
- Prefab Animator, controller assignment, disabled root motion, and
  `CommercialHeroineMotionController` valid.

The first attempt to move an Assets-local backup failed at command parse time
because of an extra semicolon in a result-expression parenthesis. No file
operation ran. The retry computed destination variables first and moved only the
exact backup plus its generated meta outside Assets. Final validation passed
after the AssetDatabase cleanup.

## Web knowledge

Official Unity 6000 documentation confirms `clipAnimations` is empty on first
import and explicitly recommends populating it in `OnPreprocessAnimation`.
Official ModelImporter documentation exposes `clipAnimations` and
`humanDescription` but does not expose the assumed warning/error properties.

## Provenance

- Import log: `logs/unity_commercial_heroine_import_retry_20260726.log`
- Validator log: `logs/unity_commercial_heroine_validation_20260726.log`
- Beads: `Clawdbot_Docker_20260125-4gia`
- Date: 2026-07-26 JST
