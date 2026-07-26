# INC-173 - Unity Player smoke and staged game integration

## Goal

Package and run the verified commercial heroine in a real Windows Player, prove
Idle > Walking > Talking > Idle and observable Humanoid motion, then integrate
the Prefab into a minimal production DatingSim scene.

## Context and protected scope

- Unity: 6000.0.73f1 (a166abc3bf0e)
- Project: `D:/Local_AI_GameDev_Master/02_UnityProject`
- Build: `F:/UnityBuilds/CommercialHeroineSmoke`
- Protected: FBX, production Prefab, Animator Controller, manifest, existing
  validation scene, web game, and Build Settings.
- Rollback: remove only the new smoke/runtime assembly, test assembly, builder,
  smoke scene, and production scene files with their `.meta` files.

## Observed facts

| Trial | Evidence | Result |
|---|---|---|
| Initial launcher | No Unity log or executable update | Parent launch observation defect |
| Build v2 | CS1626 at five `yield` statements | Failed |
| Build v3 | Linker could not resolve `nunit.framework 3.5.0` | Failed |
| Build v4 | Test asmdef could not see `LocalAIGame` | Failed |
| Build v5 | warnings=0, errors=0 | Build passed |
| Player v2 | States advanced; LeftFoot delta 0 | Failed closed |
| Build v6 / Player v3 | exit 0; 10.3514 deg; 0.510514 m | Passed |
| Production integration | scene PASS; Build Settings count 0 | Passed |
| EditMode suite | 4 total, 4 passed, 0 failed | Passed |

Operational notes: the first direct Unity launcher produced no log, so later
runs used `Start-Process -Wait` and PID/log observation. A Player command that
included deletion of an older status file was rejected before execution; the
retry preserved old evidence and used a unique output path. ByteRover query and
curate each timed out after 25 seconds under the known INC-166 condition, so no
further ByteRover retry was made and the rule was stored in Beads instead.

## 5 Why

1. Why did the packaged test not pass immediately? Build-time and runtime
   assumptions had not been exercised outside the Editor.
2. Why did compilation fail? C# iterator methods cannot yield within a try block
   that has a catch clause.
3. Why did linking fail after compilation? Tests were part of the predefined
   runtime assembly and carried NUnit into the Player.
4. Why did the first isolation attempt fail? An asmdef cannot use the predefined
   `Assembly-CSharp` as a normal assembly reference.
5. Why was runtime bone motion initially zero? Null graphics did not guarantee
   renderer-driven Animator pose updates; the isolated smoke Animator required
   `AlwaysAnimate`.

## Fishbone / FTA

- Code: unsupported iterator exception structure.
- Assembly: runtime/test boundary absent.
- Linker: unresolved test-only dependency in Player.
- Runtime: controller state advancement differed from visible-pose evaluation.
- Environment: Null graphics/headless run.
- Governance: fail-closed gate correctly prevented premature integration.

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Editor-only validation | Packaged defect escapes | 8 | 5 | 7 | 280 | Run actual Player and require JSON+exit code |
| Test dependency in runtime | Player linker fails | 7 | 4 | 3 | 84 | Runtime and Editor-test asmdefs |
| State changes but pose is culled | False animation pass | 8 | 4 | 6 | 192 | AlwaysAnimate only in headless smoke scene |
| Smoke component reaches production | Test exits real game | 9 | 2 | 3 | 54 | Separate smoke and production scenes |

## Decision rules

- IF a Unity character is declared Player-ready, THEN require a packaged Player
  run with state sequence, bone delta, evidence JSON, and exit code 0, BECAUSE
  Editor validation cannot prove linker or runtime behavior.
- IF EditMode tests coexist with product scripts, THEN use a runtime asmdef and
  an Editor-only TestAssemblies asmdef, BECAUSE test dependencies must not enter
  the Player.
- IF a headless Player measures Animator bones, THEN use `AlwaysAnimate` only in
  the smoke scene, BECAUSE renderer-based culling is not a content failure.

## Procedure

1. Build an isolated smoke scene with the verified Prefab.
2. Build Windows x64 Development Player with that scene passed explicitly to
   `BuildPipeline.BuildPlayer`; do not edit Build Settings.
3. Launch with unique `-logFile` and `-smokeStatus` paths.
4. Require Idle > Walking > Talking > Idle and measurable LeftFoot movement.
5. Require evidence state PASS and process exit 0.
6. Only then create the production scene with bootstrap, state machine,
   dialogue, schedule, stats, local LLM, and heroine references.
7. Run EditMode tests and confirm Build Settings remains empty.

## Verification artifacts

- Player JSON:
  `logs/commercial_heroine_player_smoke_v3_20260727.json`
- Player log:
  `logs/commercial_heroine_player_smoke_v3_20260727.log`
- Successful build log:
  `logs/unity_commercial_heroine_player_build_v6_20260727.log`
- Production integration log:
  `logs/unity_tokimeki_commercial_game_integration_20260727.log`
- Test result:
  `logs/unity_tokimeki_editmode_tests_20260727.xml`
- Production scene SHA-256:
  `5FA9BF96B53B7FF4A571AC74A49E139BA46A853762BC5E5672052187B6D08315`
- Smoke executable SHA-256:
  `08254FCDB980126E23125FE61FBCF3605F91D406F38F2BE26233B2A2033EBC57`

## Scope limits / next experiment

The production scene is structurally integrated but is not yet registered in
Build Settings or shipped. UI presentation, interactive schedule commands,
dialogue response quality, lip-sync, audio, and production rendering remain
separate gates. The next smallest experiment is a production-scene development
build with a non-destructive interactive UI smoke test.

## Provenance

- Date: 2026-07-27 JST
- Beads: `Clawdbot_Docker_20260125-9oie`
- Beads memory: `unity-packaged-player-gate`
- ByteRover: deferred under INC-166 after bounded query/curate timeouts
- Backup commit: `35d09d5f245b1b7bc9de8bd993057dda11942ae3`
