# INC-172 - Unity EditMode Humanoid sampling gate

## Goal and scope

Prove that the commercial heroine prefab enters Idle, Walking, Talking, and
Idle again, and that the Walking clip contains observable Humanoid motion.
Existing scenes and `ProjectSettings/EditorBuildSettings.asset` were protected.

## Observed facts

- First run: controller reached Walking, but a LeftFoot transform comparison
  driven only by `Animator.Update()` did not change and Unity exited 1.
- The FBX had already passed Avatar Human/Valid, three-clip, mapping, and
  import-warning gates.
- Corrected run: Unity exited 0 and logged LeftFoot rotation delta 34.5734
  degrees and position delta 0.379801 m.
- The final controller sequence was Idle > Walking > Talking > Idle.
- Build Settings remained `m_Scenes: []`.

## RCA

### 5 Why

1. Why did the first scene gate fail? The observed LeftFoot transform was
   unchanged.
2. Why was it unchanged? `Animator.Update()` advanced the state machine but did
   not reliably apply the EditMode Humanoid pose to the queried transform.
3. Why was the state check insufficient? State selection proves controller
   routing, not animation-curve application.
4. Why was this not detected earlier? Import validation inspected clips,
   mappings, and warnings but did not sample a pose.
5. Why did the countermeasure work? `AnimationMode.SampleAnimationClip`
   deterministically evaluates the imported clip at explicit times.

### Fishbone / logical tree

| Branch | Finding |
|---|---|
| Asset | Clip exists and previously passed import validation |
| Rig | Avatar is valid Humanoid and LeftFoot mapping exists |
| Controller | All four requested state checkpoints passed |
| Evaluation | EditMode `Animator.Update()` was the unreliable measurement path |
| Cleanup | AnimationMode lifecycle needed guaranteed termination |

### FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| State passes but pose is not measured | False commercial-quality pass | 8 | 4 | 6 | 192 | Independently sample clip at two times |
| AnimationMode remains active | Editor state contamination | 6 | 3 | 5 | 90 | Stop mode in `finally` |
| Validation scene enters production build | Unintended build content | 5 | 2 | 2 | 20 | Keep Build Settings unchanged |

## Decision rule

IF an EditMode Unity Humanoid test must prove motion, THEN validate Animator
state routing and deterministic clip pose sampling separately, BECAUSE state
advancement alone does not prove that the mapped pose changed.

## Procedure

1. Create or reopen the isolated validation scene.
2. Instantiate the production prefab without changing existing scenes.
3. Drive parameters and check Idle, Walking, Talking, then Idle states.
4. Enter `AnimationMode`, sample Walking at 0.00 and 0.45 seconds, and compare
   the LeftFoot world transform.
5. End sampling and stop `AnimationMode` in `finally`.
6. Require nonzero pose delta, save the scene, and require Unity exit 0.
7. Confirm `EditorBuildSettings.asset` remains unchanged.

## Verification and evidence

- Pass: sequence log contains `Idle>Walking>Talking>Idle`.
- Pass: rotation delta > 0.1 degree or position delta > 0.0001 m.
- Pass: Unity process return code 0.
- Pass: Build Settings remains empty.
- Final log:
  `logs/unity_commercial_heroine_scene_validation_v2_20260727.log`
- Failed log:
  `logs/unity_commercial_heroine_scene_validation_20260727.log`
- Scene:
  `D:/Local_AI_GameDev_Master/02_UnityProject/Assets/Scenes/CommercialHeroineValidation.unity`

## Recovery / rollback

Delete only the newly added validation builder and validation scene (including
their `.meta` files). The imported production prefab, FBX, controller, existing
project settings, and unrelated work are not rollback targets.

## Scope limits and next experiment

This proves import-time pose content and controller routing in an isolated
Editor scene. It does not yet prove a packaged player, frame rendering,
collision behavior, or integration with the web game. The smallest next
experiment is an isolated PlayMode/player smoke test before production-scene
integration.

## Provenance

- Date: 2026-07-27 JST
- Unity: 6000.0.73f1 (a166abc3bf0e)
- Beads: `Clawdbot_Docker_20260125-oxe7`
- Documentation trial: `bd remember --value` was rejected by the installed CLI
  before any memory write; retry used the documented positional insight syntax
  and stored key `unity-editmode-humanoid-sampling-gate`.
- Backup commit: `8addc304767ee8ce5232097c2a889c58a100942f`
