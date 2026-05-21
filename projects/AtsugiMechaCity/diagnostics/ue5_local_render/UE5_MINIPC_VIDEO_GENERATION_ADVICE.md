# UE5動画生成がうまくいかない時のミニPC向け改善アドバイス

作成日: 2026-05-21  
対象環境: ミニPC / 48GB RAM / discrete GPUなし、またはGPU能力が限定的な環境  
前提資料: `UE5_PLATEAU_RENDER_ANALYSIS.md`  
目的: UE5 + PLATEAU + Blender + ローカル素材で、失敗を減らしながら動画生成を現実的に進めるための実行方針を整理する。

---

## 0. 結論

現在の問題は、**UE5を使っているのに動画が実写風にならない**ことではなく、主に次の4点です。

1. **PLATEAU建物が箱形状中心で、実写に必要な細部が不足している**
2. **メカと都市背景を同一FBXにまとめたため、boundsやカメラが破綻しやすい**
3. **ミニPCではUE5の高負荷リアルタイム処理に頼れない**
4. **照明、露出、Sky、Fog、PBRマテリアル、道路面ディテールがまだ弱い**

したがって、方針は以下が妥当です。

> UE5を「何でも自動で実写化する道具」として使うのではなく、  
> **Blenderで整理した軽量アセット + PLATEAU位置情報 + PBR素材 + 装飾アセットを、UE5で静的にレンダーする構成**にする。

採用判断は、現時点では **ADOPT_PARTIAL** が妥当です。

---

## 1. ミニPCでの現実的なゴール

### 目指すべきゴール

ミニPCでは、いきなり以下を狙うと失敗しやすいです。

- UE5でリアルタイム高品質動画
- Lumen高品質
- Nanite大量都市
- 広域PLATEAU都市全体の高密度レンダー
- 4K動画
- メカ、都市、PBR、群衆、車両、エフェクトを全部同時に処理

まず狙うべきは以下です。

- 1280x720 または 1920x1080 の短いカット
- 5秒から15秒
- 1カメラ固定、またはゆっくりしたドリー
- 背景範囲は駅前や道路1区画だけ
- メカは別アセットとして後から配置
- UE5は静止画連番、または低負荷動画出力に使う
- 失敗時にログとレポートで原因を追える構成にする

---

## 2. 現在の成功点

添付レポートから見て、すでに以下は成功しています。

- UE5のローカル起動
- SceneCapture2Dによるヘッドレス画像出力
- BlenderからUE5向けFBX出力
- PLATEAU city-only FBXの作成
- 実座標の再センタリング
- UE5 import成功
- material slotの再割当成功
- API消費なしのローカル処理

これはかなり大きな進展です。  
ただし、**UE5に入ったこと**と、**実写品質になったこと**は別問題です。

---

## 3. 現在の失敗原因

### 3.1 PLATEAUは都市配置の土台であり、完成背景ではない

PLATEAUは以下には強いです。

- 建物位置
- 建物高さ
- 都市のスケール感
- 実在地形や道路の骨格

しかし、そのままでは以下が不足します。

- 外壁PBRテクスチャ
- 窓枠の厚み
- ベランダ
- 看板
- 店舗ファサード
- 道路汚れ
- 白線の摩耗
- 側溝
- マンホール
- 電柱
- 電線
- 信号
- 車
- 街灯
- 植栽
- 自販機
- ガードレール

そのため、PLATEAUだけをUE5に持ち込んでも、結果は「正しい位置にある箱の街」になります。

---

### 3.2 メカと背景を同一FBXにしない

メカ入りFBXでboundsが巨大化し、UE5カメラのフレーミングが壊れています。

今後は必ず分離してください。

```text
background_city_only.fbx
mecha_only.fbx
props_only.fbx
```

UE5側では、Level ScriptまたはPythonでそれぞれを配置します。

推奨構成:

```text
/Content/AtsugiMechaCity/
  Background/
    plateau_city_only/
  Mecha/
    mecha_body/
  Props/
    road_props/
    city_props/
  Materials/
    PBR_Road/
    PBR_Building/
    PBR_Glass/
  Levels/
    L_Atsugi_TestShot_001
```

---

### 3.3 combineしすぎると見た目も調整も悪くなる

city-only meshを1つの巨大StaticMeshとしてimportすると、処理は単純になりますが、以下が難しくなります。

- 道路だけ質感を変える
- 建物だけ色を変える
- 窓だけ発光させる
- 看板だけ差し替える
- 不要な建物だけ消す
- 近景だけ高品質化する

推奨は、最低でも以下に分けることです。

```text
Terrain
Road
Sidewalk
Buildings
Windows
Signs
Rails
Plaza
StreetProps
```

---

## 4. ミニPC向けの最重要方針

### 方針A: UE5は最終ステージとして使う

UE5だけで全部やろうとしないでください。

おすすめの役割分担:

| 工程 | 推奨ツール | 理由 |
|---|---|---|
| PLATEAU整理 | Blender | 軽量化、分割、再センタリングがしやすい |
| PBR素材準備 | Blender / Python | ローカル素材を整理しやすい |
| 装飾生成 | Blender / Python | 低ポリ車両、信号、電柱などを自動配置しやすい |
| 最終配置 | UE5 | カメラ、ライト、ポスト処理が強い |
| レンダー | UE5 SceneCapture2D / Movie Render Queue | 見た目確認と動画出力 |
| 比較・レポート | Python | 成功/失敗を記録しやすい |

---

### 方針B: いきなり動画ではなく、静止画比較から始める

動画生成の前に、必ず以下を作ります。

```text
shot_001_baseline.png
shot_001_lighting_fixed.png
shot_001_pbr_road.png
shot_001_pbr_building.png
shot_001_props_added.png
shot_001_final_preview.png
```

1枚ずつ改善して、見た目が上がったか確認してから動画化します。

---

### 方針C: 近景だけ本気で作る

広い街全体を実写化するのは、ミニPCには重すぎます。  
カメラに映る範囲だけを重点的に作ります。

優先順位:

1. カメラ手前の道路
2. 手前左右の建物
3. 信号、標識、街灯
4. メカの接地面
5. 遠景のビル
6. 空

遠景は簡略化して問題ありません。

---

## 5. まず直すべきUE5設定

### 5.1 Sky / Light / Fog を標準化する

黒背景や暗すぎる画面は、アセット品質以前に照明セットアップの問題です。

最低限入れるもの:

```text
DirectionalLight
SkyLight
SkyAtmosphere
ExponentialHeightFog
PostProcessVolume
```

PostProcessVolumeでは以下を固定します。

```text
Auto Exposure: OFF
Exposure Compensation: 固定
White Balance: 固定
Bloom: 弱め
Vignette: 弱め
Motion Blur: 低め、またはOFF
```

ミニPCでは、見た目の安定を優先して、まず自動露出を切るべきです。

---

### 5.2 Lumenに頼りすぎない

discrete GPUなしのミニPCでは、Lumenや高品質GIに頼ると重くなります。

推奨:

- 最初は Lumen OFF または低設定
- Static / Stationary Light中心
- 影の品質は中以下
- 反射はScreen Space Reflection低め
- 高品質レンダーは最後だけ

---

### 5.3 カメラを道路面に近づける

上空から広い街を見ると、PLATEAUの箱感が目立ちます。  
実写っぽく見せるには、道路面に近いローアングルが有効です。

推奨カメラ:

```text
高さ: 120cm〜170cm
焦点距離: 28mm〜45mm
注視点: 道路奥またはメカ
画角内: 道路、建物ファサード、空をバランスよく入れる
```

---

## 6. Blender側でやるべき前処理

### 6.1 必ず分割exportする

今後のexportは以下のように分けます。

```text
export_terrain.fbx
export_road.fbx
export_sidewalk.fbx
export_buildings.fbx
export_windows.fbx
export_signs.fbx
export_rails.fbx
export_city_props.fbx
export_mecha.fbx
```

最低限でも以下は分けてください。

```text
city_terrain_road.fbx
city_buildings.fbx
city_facades.fbx
mecha_only.fbx
```

---

### 6.2 bounds reportを必ず出す

FBX出力時には、毎回JSONで以下を記録します。

```json
{
  "asset": "city_buildings.fbx",
  "unit": "meter_to_ue_cm",
  "origin_policy": "center_xy_min_z",
  "bounds_m": {
    "min": [-300.0, -300.0, 0.0],
    "max": [300.0, 300.0, 80.0]
  },
  "object_count": 1200,
  "mesh_count": 1200,
  "material_count": 12
}
```

boundsが異常なら、UE5に入れる前に止めます。

---

### 6.3 遠景を減らす

ミニPCでは、広域全体を読み込むより、カメラ周辺だけ切り出すほうが成功します。

推奨:

```text
最初のテスト範囲: 半径100m
次の範囲: 半径200m
最終でも: 半径300m程度
```

今回のような約591m x 583mの範囲は、評価には使えますが、実写化の最初の範囲としては広すぎます。

---

## 7. PBR素材の使い方

### 7.1 最初に入れるべき素材

効果が高い順です。

1. 道路アスファルト
2. 歩道コンクリート
3. 建物外壁
4. ガラス
5. 白線
6. 金属
7. 看板発光
8. 汚れデカール

特に道路は、画面の大部分を占めるため最優先です。

---

### 7.2 ローカル素材フォルダを標準化する

OpenClaw側で以下のような素材フォルダを持つとよいです。

```text
data/workspace/apps/blender_assets/ambientcg/
  asphalt/
  concrete/
  building_wall/
  glass/
  metal/
  tiles/
  decals/
```

UE5側では以下に変換します。

```text
/Content/AtsugiMechaCity/Materials/PBR/
  M_Road_Asphalt
  M_Sidewalk_Concrete
  M_Building_Wall_A
  M_Building_Wall_B
  M_Window_Glass_Dark
  M_Sign_Emissive
  M_Decal_Dirt
```

---

## 8. 装飾アセットを追加する

PLATEAUの箱感を消すには、建物を全部作り直すより、近景に装飾を追加するほうが効果的です。

### 優先して追加するもの

```text
信号
標識
街灯
電柱
電線
ガードレール
車
自販機
マンホール
道路汚れ
植栽
店舗看板
窓枠パネル
室外機
配管
ベランダ風パーツ
```

### 最初は低ポリでよい

ミニPCでは、最初から高精細アセットを大量投入しないでください。  
低ポリでも、数と配置が増えると実写感は上がります。

---

## 9. UE5動画化の推奨ステップ

### Step 1: 静止画レンダー

```text
SceneCapture2D
TextureRenderTarget2D
EXR出力
FFmpegでPNG変換
```

これは添付レポート上でも安定しているため、当面の標準方式にします。

---

### Step 2: 連番出力

まずは動画ファイルではなく、PNGまたはEXR連番を出します。

```text
frames/
  shot001_0001.png
  shot001_0002.png
  shot001_0003.png
```

その後にFFmpegで動画化します。

```bash
ffmpeg -framerate 24 -i shot001_%04d.png -c:v libx264 -pix_fmt yuv420p shot001_preview.mp4
```

---

### Step 3: 5秒だけ作る

最初の合格基準:

```text
解像度: 1280x720
FPS: 24
長さ: 5秒
フレーム数: 120
カメラ: 1つ
メカ: あり、またはなし
```

これで成功したら、10秒、15秒へ伸ばします。

---

## 10. 失敗しにくい実装順序

以下の順番を守ると、原因追跡がしやすくなります。

```text
1. city-only / 半径100m / PBRなし / ライトあり
2. city-only / 半径100m / PBR道路のみ
3. city-only / 半径100m / PBR建物追加
4. city-only / 半径100m / 信号・街灯・車を追加
5. city-only / 半径100m / ローアングルカメラ
6. mecha-onlyを別import
7. mechaと地面の接地調整
8. 静止画レンダー
9. 120フレーム連番
10. mp4化
```

---

## 11. OpenClaw / Codexへ渡す実装指示

以下をそのままCodexまたはOpenClawに渡せます。

```text
目的:
UE5 + PLATEAU + Blenderで、ミニPC向けに失敗しにくい動画生成パイプラインを作る。

採用判断:
ADOPT_PARTIAL。
UE5/PLATEAUフローは採用候補だが、現状は完成フローではない。
背景とメカは分離し、PBR素材と装飾アセットを追加して段階的に改善する。

必須方針:
1. メカと背景を同一FBXにまとめない。
2. city-only背景を、Terrain/Road/Sidewalk/Buildings/Windows/Signs/Rails/Propsに分割する。
3. Blender export時にbounds JSON reportを必ず出す。
4. UE5 import時にbounds、material slot、camera targetをreport化する。
5. SceneCapture2D + RenderTarget + EXR exportを標準レンダー方式にする。
6. HighResShotやEditor viewport依存は使わない。
7. まず静止画比較を行い、合格後に5秒動画化する。
8. 最初の対象範囲は半径100mに制限する。
9. Lumenや高負荷設定は初期段階では使わない。
10. PBR素材は道路、歩道、建物、窓、看板の順に適用する。

実装してほしいファイル:
- scripts/blender/export_city_split_for_ue5.py
- scripts/ue5/import_city_split_render.py
- scripts/ue5/setup_lighting_postprocess.py
- scripts/ue5/apply_pbr_materials.py
- scripts/ue5/render_still_and_frame_sequence.py
- config/ue5_minipc_render_profile.json
- docs/UE5_MINIPC_PIPELINE.md
- reports/render_comparison_template.md

最初のテスト:
- 半径100mのcity-only背景
- メカなし
- ローアングルカメラ
- SkyAtmosphere / DirectionalLight / SkyLight / ExponentialHeightFog / PostProcessVolumeあり
- 1280x720静止画
- 3パターン出力
  1. baseline
  2. pbr_road
  3. pbr_road_building_props

合格条件:
- 黒背景にならない
- カメラが都市を正しく捉える
- 道路面が見える
- 建物が灰色一色ではない
- ログにbounds異常がない
- 出力PNGを人間が比較できる
```

---

## 12. 具体的な設定案

### 12.1 ミニPC用レンダー設定

```json
{
  "target_resolution": [1280, 720],
  "fps": 24,
  "duration_sec_first_test": 5,
  "render_mode": "SceneCapture2D_RenderTarget_EXR",
  "use_lumen_initially": false,
  "use_nanite_initially": false,
  "use_virtual_shadow_maps_initially": false,
  "camera_height_cm": 150,
  "camera_lens_mm": 35,
  "city_radius_m_first_test": 100,
  "city_radius_m_max_initial": 300,
  "asset_policy": {
    "background_and_mecha_separate": true,
    "combine_all_meshes": false,
    "pbr_first_targets": ["road", "sidewalk", "building", "window", "sign"]
  }
}
```

---

### 12.2 カメラ案

```json
{
  "shot_001": {
    "name": "low_angle_road_mecha",
    "camera_location_cm": [-600, -1200, 150],
    "look_at": [0, 0, 180],
    "lens_mm": 35,
    "purpose": "道路面と建物ファサードを見せる"
  },
  "shot_002": {
    "name": "station_square_wide",
    "camera_location_cm": [-1800, -2400, 240],
    "look_at": [0, 0, 180],
    "lens_mm": 28,
    "purpose": "街の広がりを見る"
  },
  "shot_003": {
    "name": "mecha_close_background",
    "camera_location_cm": [-500, -900, 170],
    "look_at": [0, 0, 220],
    "lens_mm": 45,
    "purpose": "メカを主役にして背景の箱感を目立たせない"
  }
}
```

---

## 13. やってはいけないこと

```text
NG 1: PLATEAU広域全部を一気に高品質化しようとする
NG 2: メカと都市を同じFBXにまとめる
NG 3: UE5に入れれば自動的に実写になると考える
NG 4: いきなり動画を出そうとする
NG 5: 失敗画像だけ見て原因を推測し、ログを見ない
NG 6: Lumen/Nanite/高品質影を最初から全部ONにする
NG 7: 灰色の箱のままカメラだけ変えて粘る
NG 8: 1つの巨大StaticMeshにcombineして素材調整不能にする
NG 9: PBRなしで実写感を求める
NG 10: 遠景まで全部作り込む
```

---

## 14. 優先タスクリスト

### 最優先

- [ ] 背景とメカを完全分離
- [ ] city-onlyを分割export
- [ ] 半径100mのテストシーン作成
- [ ] Sky/Light/Fog/PostProcess標準化
- [ ] SceneCapture2D出力のテンプレート化
- [ ] 道路PBR適用
- [ ] ローアングルカメラ追加

### 次点

- [ ] 建物PBR適用
- [ ] 窓ガラスmaterial改善
- [ ] 看板emissive追加
- [ ] 信号/街灯/車/電柱を低ポリ追加
- [ ] 5秒連番レンダー
- [ ] FFmpegでmp4化

### その後

- [ ] メカ別import
- [ ] 接地調整
- [ ] 15秒動画化
- [ ] 1920x1080化
- [ ] 複数カメラ化
- [ ] Telegram送信
- [ ] Portalカード化

---

## 15. 最終判断

このUE5/PLATEAU動画生成フローは、**捨てる必要はありません**。  
むしろ、すでにUE5 import、SceneCapture2D出力、PLATEAU再センタリングまで到達しているため、土台としては有望です。

ただし、今のままでは実写品質には届きません。

正しい次の一手は、UE5そのものを疑うことではなく、以下です。

```text
PLATEAU = 位置と都市骨格
PBR素材 = 実写感
装飾アセット = 街らしさ
UE5 = 最終レンダー
Blender = 整理と軽量化
Python = 自動化とレポート
```

この分担に変更すれば、ミニPCでも「時間はかかるが、失敗原因を追える動画生成」に近づけます。

---

## 16. 推奨ファイル名

この方針をOpenClawに読ませる場合は、以下の名前で保存してください。

```text
docs/UE5_MINIPC_VIDEO_GENERATION_ADVICE.md
```

または、今回の診断ログと同じ場所なら以下です。

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_MINIPC_VIDEO_GENERATION_ADVICE.md
```
