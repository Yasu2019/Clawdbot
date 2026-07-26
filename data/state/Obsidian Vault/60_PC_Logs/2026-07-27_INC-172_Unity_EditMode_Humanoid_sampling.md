# INC-172 Unity EditMode Humanoid sampling

## QC工程表

| 工程 | 入力 | 管理項目 | 合格基準 | 結果 |
|---|---|---|---|---|
| Scene生成 | CommercialHeroine prefab | 既存Scene非変更 | 専用Sceneのみ生成 | PASS |
| Controller評価 | Speed / IsTalking | 状態遷移 | Idle > Walking > Talking > Idle | PASS |
| Pose評価 | Walking clip | LeftFoot変化 | 0.1度超または0.0001m超 | 34.5734度 / 0.379801m |
| 終了処理 | AnimationMode | 状態汚染防止 | finallyで停止 | PASS |
| Project保護 | Build Settings | Scene登録 | 0件のまま | PASS |

## 5Why

1. 初回検証は左足変化が0で停止した。
2. Animator.UpdateはEditModeで状態を進めてもHumanoid姿勢の測定保証にはならなかった。
3. Controller状態とClip姿勢を同じ指標とみなしていた。
4. Import品質ゲートには時刻指定のPoseサンプリングがなかった。
5. AnimationModeによる決定論的サンプリングを追加し、測定を分離した。

## FTA / Fishbone

- Asset: Clip存在、Import警告0。
- Rig: Human/Valid、LeftFoot割当あり。
- Controller: 4状態チェック合格。
- Measurement: 初回のAnimator.Update評価だけが不適切。
- Environment: Unity 6000.0.73f1 batchmode。

## FMEA

| 故障モード | 影響 | RPN | 対策 |
|---|---|---:|---|
| 状態だけでMotion合格にする | 偽陽性 | 192 | Clipを2時刻で独立サンプル |
| AnimationModeを閉じない | Editor汚染 | 90 | finallyでStop |
| 検証SceneをBuildへ混入 | 製品構成変化 | 20 | Build Settingsを空のまま保護 |

## 対策・検証

`AnimationMode.SampleAnimationClip`で0.00秒と0.45秒を比較。LeftFootは
34.5734度、0.379801m変化した。Idle > Walking > Talking > Idleが合格し、
Unity終了コード0。既存Sceneなし、Build Settingsの`m_Scenes: []`も維持。

## 再利用ルール

IF EditModeでHumanoid Motionを証明する THEN Controller状態確認とClip姿勢
サンプリングを分離する BECAUSE 状態遷移だけでは骨Pose変化を証明できない。

## ロールバック

対象は新規のValidationSceneBuilder、Validation Scene、および各metaのみ。
製品Prefab、FBX、Controller、ProjectSettingsは対象外。

## Provenance

- Beads: Clawdbot_Docker_20260125-oxe7
- Beads memory: unity-editmode-humanoid-sampling-gate
- 記録試行: `--value`は現行CLIで未対応、位置引数形式へ修正して成功。
- Backup: 8addc304767ee8ce5232097c2a889c58a100942f
- Log: logs/unity_commercial_heroine_scene_validation_v2_20260727.log
