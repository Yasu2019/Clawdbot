# INC-165 Mixamo Retarget v23

## Goal

既存MixamoライブラリからIdle、Walking、Talkingを商用ヒロインv23へ安全に移植する。

## Facts

- Sources: `Idle.fbx` 251 frames, `Walking.fbx` 42 frames, `Talking.fbx` 151 frames
- Source skeleton: Mixamo standard 65 bones
- Target skeleton: 19 bones
- First attempt: zombie arms, crossed legs, source character visible
- Final: GLB/FBX both retain 3 actions, 19 bones, 8 materials
- Gate: `PASS_MIXAMO3_RETARGET`

## 5 Why

1. 腕と脚が不自然：親変形を子ボーンへ重複適用した。
2. 重複した理由：`pose.matrix`を独立差分として扱った。
3. 初期姿勢もずれた：Mixamo Tポーズ固定オフセットをAポーズへ適用した。
4. 元モデルが写った：プレビュー後にsource objectsを削除していた。
5. GLB警告が出た：source actionのユーザーを解除せず残した。

## Countermeasures

- `matrix_basis`を使用する。
- source開始フレームとの差分だけを転送する。
- source/target rest軸間でQuaternionを変換する。
- プレビューとエクスポート前にsource objects/actionsを削除する。
- GLB/FBXを空のBlenderへ再読込して3アクションを確認する。

## Verification

| Format | Actions | Bones | Materials | Result |
|---|---:|---:|---:|---|
| GLB | 3 | 19 | 8 | PASS |
| FBX | 3 | 19 | 8 | PASS |

Visual QA: Idle, Walking, Talking all PASS. No source-character contamination or skirt tearing.

## Rollback

Original `commercial_v23` remains unchanged. Delete only `commercial_v23_mixamo3_v3` if rollback is needed.

## Scope limits

Finger animation is omitted because the target has no finger bones. Unity Humanoid import and in-engine foot-ground correction remain separate validation stages.

## Provenance

- Date: 2026-07-26 JST
- Incident: INC-165
- Validation: `commercial_v23_mixamo3_v3/commercial_heroine_v23_mixamo3_validation.json`
