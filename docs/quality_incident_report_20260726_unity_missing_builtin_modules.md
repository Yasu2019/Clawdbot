# Unity import blocked by missing Physics and Video built-in modules (2026-07-26)

## Goal and impact

Goal: import the verified commercial heroine FBX into Unity 6000.0.73f1 and
generate a Humanoid Animator controller plus prefab.

Unity started successfully, validated an unlimited Unity Personal license,
resolved packages, and rebuilt the Library. Script compilation then returned
code 1 before the heroine importer could execute. No controller or prefab was
created. Existing scenes and legacy controllers were not modified.

## Observed facts

- Unity version: `6000.0.73f1 (a166abc3bf0e)`.
- Project: `D:\Local_AI_GameDev_Master\02_UnityProject`.
- FBX SHA-256:
  `6285CE1EF1E57EFEBFAA9A3E8330D23BD979A2848B0252168FA12225B5DA80C1`.
- `Packages/manifest.json` contains neither `com.unity.modules.physics` nor
  `com.unity.modules.video`.
- Five compiler errors:
  - two `CS1069` errors for `UnityEngine.CharacterController`, forwarded to
    `UnityEngine.PhysicsModule`;
  - three `CS1069` errors for `VideoPlayer`/`VideoClip`, forwarded to
    `UnityEngine.VideoModule`.
- The Unity compiler explicitly says to enable the built-in Physics and Video
  packages.
- No error references `CommercialHeroineMotionController.cs` or
  `CommercialHeroineMixamoImporter.cs`.

## Root cause analysis

### 5 Whys

1. The controller and prefab were not created because executeMethod never ran.
2. It never ran because project script compilation failed.
3. Compilation failed because existing gameplay/video scripts reference types
   in disabled built-in modules.
4. The modules were disabled because the project manifest omitted the Physics
   and Video dependencies.
5. The placeholder project had never completed a real Unity 6 compile/import,
   so its minimal manifest was not validated against all existing scripts.

### Fishbone / FTA

- Code: existing scripts require CharacterController and VideoPlayer.
- Configuration: two built-in packages are absent (confirmed root cause).
- Editor/license: ruled out; editor and license initialized successfully.
- Character asset: ruled out as compilation stopped before importer execution.
- Network/package registry: slow initial resolution completed successfully.

## FMEA

| Failure mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Physics module omitted | 7 | 5 | 2 | 70 | Add direct built-in dependency |
| Video module omitted | 6 | 5 | 2 | 60 | Add direct built-in dependency |
| Character code blamed for project error | 6 | 4 | 6 | 144 | Attribute errors by file and assembly |
| Broad package changes cause drift | 7 | 3 | 4 | 84 | Add only two `1.0.0` module lines |

## Proposed countermeasure

1. Back up `Packages/manifest.json`.
2. Add only:
   - `"com.unity.modules.physics": "1.0.0"`
   - `"com.unity.modules.video": "1.0.0"`
3. Re-run the same Unity batch command.
4. Require exit code 0, zero compiler errors, valid Humanoid avatar, three clips,
   generated controller/prefab, and no existing scene changes.

Decision rule: IF an existing Unity type is forwarded to a built-in module and
the compiler says to enable that package, THEN add the matching built-in module
as a direct manifest dependency, BECAUSE built-in packages toggle Unity engine
features and omitted modules are intentionally excluded.

## Verification, rollback, and scope

Current pass/fail: FAIL-CLOSED. No generated controller or prefab exists.
Rollback for the proposed change is the timestamped manifest backup plus the
existing ProjectVersion backup
`ProjectVersion.txt.bak_20260726_205720`. Library is regenerable cache.

Final result: the two dependencies were added after backup. Unity registered both
built-in modules, compiled with zero errors, imported 715 assets, generated the
controller and prefab, and exited 0. The later full quality gate also passed.

## Web knowledge

Bounded official-only search was used. Unity documents built-in packages as
feature toggles, identifies `com.unity.modules.video` as the Video module, and
states that project dependencies are declared in `Packages/manifest.json`.
These findings confirm the local compiler's prescribed correction.

## Provenance

- Log: `logs/unity_commercial_heroine_import_20260726.log`
- Manifest SHA-256 before correction:
  `835AF4AABFF28C24634F318306C0E1B4F119FE8CCD5F39EFC179D2C84F8E2195`
- Beads: `Clawdbot_Docker_20260125-4gia`
- Date: 2026-07-26 JST
