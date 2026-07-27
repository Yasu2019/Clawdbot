# INC-174: Tokimeki commercial UI, lip-sync, and render integration

## Scope and facts

| Item | Evidence |
|---|---|
| Goal | Integrate production UI, dialogue operation, schedule selection, lip sync, and actual-screen rendering |
| Unity | 6000.0.73f1 |
| Production scene | `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Scenes\TokimekiCommercialGame.unity` |
| Source facial capability | 1 SkinnedMeshRenderer, 0 BlendShapes, Head present, Jaw absent |
| Final Player | `F:\UnityBuilds\TokimekiCommercialRender\TokimekiCommercialRender.exe`, exit 0 |
| Final image | `logs/tokimeki_commercial_render_v6_20260727.png`, 113,191 bytes |
| Functional evidence | 2 interactions, Study selected, dialogue nonempty, lip peak 0.9817447 |

## Failure chronology and 5 Whys

1. The first build failed with `CS0103` for `ScreenCapture`.
   Why: the screen-capture Unity module was not declared. The manifest was
   backed up and only `com.unity.modules.screencapture` was added.
2. The first capture was black and only 9,740 bytes.
   Why: hidden/batch-mode D3D rendering did not produce a presentable frame.
   The size gate was retained and capture moved to a normal windowed Player.
3. Automation then reported no completed interaction.
   Why: `ApplyDialogue` displayed the line but did not increment the evidence
   counter. The real callback now increments it.
4. Intermediate images cropped the character or made it too small.
   Why: static camera assumptions and later the generated mouth contaminated
   bounds. Auto-framing now uses only the original `SkinnedMeshRenderer`.
5. The mouth floated and became oversized.
   Why: it inherited the FBX Head transform scale. `LateUpdate` now applies
   Head-relative position and size in world space.
6. The next image had face-overlapping stats and a white ground edge.
   Why: UI anchoring and ground coverage were not judged at final resolution.
   The stats were moved left and ground scale increased before the sixth render.

## Fishbone / logical tree

- Dependency: missing screenshot module.
- Runtime environment: hidden/batch-mode capture returned black pixels.
- Instrumentation: interaction counter absent from the applied-dialogue path.
- Geometry: generated mouth included in framing bounds.
- Transform hierarchy: imported Head scale propagated to the mouth.
- Presentation: stats anchor and ground extent were visually insufficient.
- Source asset: no BlendShape/Jaw capability for native facial deformation.

## FMEA

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Black capture | False evidence | PNG size and visual inspection | Visible Player capture; fail below 10 KB |
| Callback not counted | Smoke fails or lies | JSON interactions | Count only completed real callbacks |
| Generated geometry in bounds | Bad framing | Image review | Original skinned bounds only |
| Parent-scale mouth | Floating/oversized mouth | Image review | World-space `LateUpdate` |
| UI/ground obstruction | Commercial presentation defect | Full-resolution review | Final-layout visual gate |

## QC process and verification

1. Back up production scene, builder, and manifest before changes.
2. Build with warning/error gate: pass only at 0/0.
3. Run EditMode tests: 4 passed, 0 failed.
4. Run packaged Player with `-renderSmoke`.
5. Require exit 0, JSON `PASS`, at least two interactions, nonempty dialogue,
   lip peak above 0.2, and screenshot of at least 10 KB.
6. Inspect the full-resolution image for face visibility, mouth alignment,
   character framing, UI readability, and ground coverage.
7. Confirm Build Settings scene count remains zero and the production scene has
   no render-smoke component.

## Decision rule and rollback

IF a model has neither BlendShapes nor a Jaw bone, THEN do not claim native or
phoneme-accurate lip sync; use an explicitly labelled visual fallback only when
it follows the Head in world space and passes a real-screen image gate, BECAUSE
controller state alone does not prove visual alignment.

Rollback uses
`D:\Local_AI_GameDev_Master\_unity_project_backups\02_UnityProject_20260727_ui_lipsync`
and `Packages\manifest.json.bak_20260727_ui_render`. Build Settings was not
modified.

## Scope limits and next experiment

The deterministic dialogue line verifies UI-to-dialogue-to-mouth integration
without cloud/API cost. It does not prove microphone/audio phoneme accuracy or
every LocalLLM response. The smallest next experiment is to add real facial
BlendShapes to the source character, map visemes, and compare audio-envelope
timing against this fallback.

## Provenance

- Date: 2026-07-27 JST
- Beads: `Clawdbot_Docker_20260125-xpi2`
- Build log: `logs/unity_tokimeki_commercial_presentation_build_v6_20260727.log`
- Player JSON: `logs/tokimeki_commercial_render_smoke_v6_20260727.json`
- Screenshot SHA-256:
  `DE3CD317E4DB91EC737957FE3812E26A772B801B822F24EDB6A895CF7D2D1187`
