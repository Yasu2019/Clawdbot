# INC-164 Commercial Heroine v23

## Goal

2Dデザインを維持した恋愛シミュレーション／ブラウザ／モバイル向けの商用スタイライズ3Dキャラクターを、外部生成APIなしで完成させる。

## Context

- Machine: Windows K10
- Blender: 5.1.1
- Design: 茶髪、白ジャケット、青緑トップ、濃灰スカート、赤い裾、黒タイツ、茶ブーツ
- Constraint: MeshyAI不使用。AtsugiMechaCityの歩行学習は停止しない
- Backup: `backup/heroine-v21-pre-commercial-20260726`, commit `df94149be2`

## Observed facts

- v21以前は腕とスカートが同一トポロジーだった。
- v20は橋渡し面を1,067枚削除し、腰に欠損が生じた。
- v23は21,452三角形、8材質、19ボーン、19頂点グループ。
- 元メッシュとFBX再読込は境界0、非多様体0。
- GLB/FBX再読込ゲートは `PASS_COMMERCIAL_STYLIZED`。

## 5 Why / FTA

1. ポーズ時のスカート伸長は腕ウェイト混入による。
2. ウェイト除去後も同一三角形が腕とスカートを接続した。
3. 面削除では接着範囲が広く、腰欠損を生じた。
4. 一つの連続面へ相反する変形を要求していた。
5. 商用アニメーションには関節・衣装ごとの明確な境界が必要だった。

## Fishbone / FMEA

| Category / failure | Effect | Countermeasure |
|---|---|---|
| Geometry: arm/skirt fusion | Pose tearing | Closed modular parts |
| Rig: automatic-weight contamination | Clothing deformation | Rigid named groups |
| Rendering: missing World | Render abort | Create World explicitly |
| Validation: GLB seam split | False failure | Source/FBX topology authority |
| Process: rest-only review | Hidden deformation | Rest plus pose visual QA |

## Procedure

1. 独立した閉メッシュ部品を生成。
2. PBR材質を8系統割当。
3. 19ボーンと同名頂点グループを作成。
4. レスト／左右非対称ポーズをレンダー。
5. BLEND、GLB、FBXを出力。
6. 空のBlenderへGLB/FBXを再読込。
7. ボーン、材質、グループ、FBX閉メッシュを検査。

## Verification

- Visual rest and pose review: PASS
- Bones/groups/materials: 19 / 19 / 8
- Source and FBX boundary/non-manifold: 0 / 0
- GLB and FBX reimport: PASS
- Final: `PASS_COMMERCIAL_STYLIZED`

## Recovery / rollback

問題時はバックアップブランチのv21生成器へ戻す。v1-v21成果物は変更していない。

## Scope limits

商用スタイライズ／低ポリ品質。写実AAA人物、表情シェイプキー、Mixamo全85モーションは未検証。

## Next experiment

Unity 6 Humanoidへv23 FBXを読み込み、歩行・待機・会話モーション各1件で衣装貫通を確認する。

## Provenance

- Date: 2026-07-26 JST
- Beads: `Clawdbot_Docker_20260125-js8z`
- Incident: INC-164
- Validation: `commercial_v23/commercial_heroine_v23_reimport_validation.json`
