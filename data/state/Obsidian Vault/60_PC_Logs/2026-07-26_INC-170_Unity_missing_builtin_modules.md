# INC-170 Unity missing built-in modules

## QC process record

| Gate | Result | Evidence |
|---|---|---|
| Unity 6000.0.73f1 startup | PASS | Correct revision in log |
| Unity Personal license | PASS | Assigned/ULF, Unlimited |
| Package resolution | PASS | 15 packages registered |
| Whole-project compile | FAIL | Five CS1069 errors |
| Heroine importer execution | NOT RUN | Compile stopped executeMethod |
| Controller/prefab | ABSENT | Both paths do not exist |

## 5 Why / FTA

The importer did not run because compilation failed. Compilation failed because
existing gameplay and cinematic scripts reference CharacterController and
VideoPlayer/VideoClip. Those types are forwarded to PhysicsModule and
VideoModule, but the project manifest omitted both built-in packages. Editor,
license, FBX hash, and network package resolution passed and are not root causes.

## Fishbone

- Code: existing scripts legitimately reference two engine modules.
- Configuration: Physics and Video toggles are absent from manifest.
- Asset: commercial heroine scripts produced no errors.
- Environment: correct editor and license.
- Method: the placeholder project had not undergone a real full compile.

## FMEA

| Mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| Physics omitted | 7 | 5 | 2 | 70 | Add module 1.0.0 |
| Video omitted | 6 | 5 | 2 | 60 | Add module 1.0.0 |
| Wrong blame | 6 | 4 | 6 | 144 | Attribute by file/assembly |
| Dependency drift | 7 | 3 | 4 | 84 | Surgical two-line addition |

## Countermeasure / rollback

Back up `Packages/manifest.json`; add only
`com.unity.modules.physics` and `com.unity.modules.video` version `1.0.0`;
repeat the batch run; require zero compiler errors and generated assets.
Rollback restores the timestamped manifest backup. Library is disposable cache.

## Scope / provenance

The correction is proposed but not yet executed. Source:
`logs/unity_commercial_heroine_import_20260726.log`, INC-170, Beads
`Clawdbot_Docker_20260125-4gia`, 2026-07-26 JST.
