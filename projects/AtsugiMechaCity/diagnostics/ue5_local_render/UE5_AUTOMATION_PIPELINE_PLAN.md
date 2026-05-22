# UE5 Automation Pipeline Plan

作成日: 2026-05-22 JST

目的:

Twinmotion の手動 Import 反復をやめ、最終パイプラインを UE5 自動化へ寄せる。Twinmotion は短期の lookdev / 参考確認に限定し、最終的な街背景生成、カメラ、レンダー、記録、Telegram 送信は UE5 側で再現可能にする。

## 採用判断

判定: ADOPT_UE5_AUTOMATION_PRIMARY

理由:

- Twinmotion は短時間で風景をリアルに寄せやすいが、GUI Import と位置合わせが手作業になる。
- Codex から Twinmotion GUI への安定操作は現環境では成立しない。
- UE5 には既に Python による Import、SceneCapture2D、EXR export、PNG変換、比較レポートの実績がある。
- 反復作業、自動レンダー、RickDias 合成、Telegram 送信、Markdown記録は UE5 側の方が自動化しやすい。

No-go:

- Twinmotion を毎回の必須工程にしない。
- GUI クリック自動化を本番工程にしない。
- Terrain / Buildings の Z 差を未検証のまま最終レンダーに使わない。
- RickDias は街だけの品質が合格するまで置かない。

## Repo Scan

既存資産:

- `ue5_render_radius100_comparison.py`
  - 最有力の拡張元。
  - split FBX import、カテゴリ別 material、props、SceneCapture2D、EXR export、report JSON が既にある。
- `export_city_split_radius100_for_ue5.py`
  - Blender 側から Terrain / Road / RoadMarkings / Sidewalk / Buildings / Windows / Signs / Rails を分離出力できる。
- `radius100_compare/radius100_ue5_compare_report.json`
  - UE5 自動比較レンダーの実績。
- `TWINMOTION_LOOKDEV_ADOPTION_PLAN.md`
  - Twinmotion は ADOPT_PARTIAL。最終パイプラインではなく lookdev 補助。
- `twinmotion_lookdev/notes/atsugi_screenshot_review_20260522.md`
  - Terrain が Z=16.8m から 20.4m、Buildings が Z=0m 付近にある二重構造問題を記録済み。

重複判断:

- 新規アプリは不要。
- 既存 UE5 render scripts を拡張する。
- まず `ue5_render_radius100_comparison.py` 系を本番候補に昇格させる。

## 基本方針

1. Blender 側で都市要素を分割・再センタリングする。
2. Terrain は最初から本番投入しない。必要なら別レイヤーとして扱う。
3. UE5 側では Road / Sidewalk / Buildings / Windows / Signs / Rails をカテゴリごとに import する。
4. UE5 Python で PBR 風 material、道路、歩道、店舗、看板、街灯、車、樹木を追加する。
5. 街だけで合格してから RickDias を配置する。

## Pipeline v1

### Stage 1: Clean City Import

入力:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/radius100_split/*.fbx
```

処理:

- Terrain を optional にする。
- Road / Sidewalk / Buildings / Windows / Signs / Rails を優先。
- 地下/地上の二重構造が出ない構成を標準にする。

出力:

```text
radius100_compare/r100_clean_city.exr
radius100_compare/r100_clean_city.png
radius100_compare/r100_clean_city_report.json
```

### Stage 2: Street Readability

追加するもの:

- foreground asphalt road
- curb / sidewalk panels
- crosswalk
- lane markings
- guard rails
- traffic lights
- street lights
- cars
- trees
- storefront panels
- poster/sign panels

合格条件:

- RickDias なしで街に見える。
- 道路、歩道、建物、車、樹木、街灯の関係が読める。
- Terrain の上下面が天井や地下に見えない。

### Stage 3: Cinematic Camera

推奨:

```text
camera_height: 1.6m to 4.0m equivalent
lens: 35mm to 50mm equivalent
sun_angle: low side light
target: road intersection plus building frontage
```

UE5側:

- SceneCapture2D を標準。
- HighResShot は補助。ヘッドレスで不安定なため本線にしない。

### Stage 4: RickDias Integration

前提:

- 街だけのレンダーが合格済み。

処理:

- RickDias を最後に配置。
- 足元スケールと接地を確認。
- 街要素に対してサイズが破綻しないか確認。

## 次の実装単位

最初の実装候補:

```text
ue5_render_radius100_comparison.py
```

に以下を追加する。

- `ENABLE_TERRAIN = False` のような明示フラグ。
- `clean_city_terrain_off` variant。
- report に terrain enabled/disabled を記録。
- Twinmotion で得た教訓を反映した低視点 camera preset。
- props density を上げた `street_readability_v1` variant。

## 検証

最低限:

- UE5 Python が完走する。
- EXR が生成される。
- PNG 変換が成功する。
- report JSON に variant と設定が残る。
- 画像上で地下/地上二重構造が消える。

望ましい:

- contact sheet を生成し、baseline / terrain_off / street_readability を比較できる。
- Telegram 送信用の代表PNGを1枚選べる。

## 現時点の結論

最終パイプラインは UE5 自動化へ寄せる。Twinmotion は参考 lookdev として価値があるが、Import/位置合わせが手作業であり、Codex が安定操作できないため本番反復工程にはしない。

## 実装ログ 2026-05-22

対象:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_radius100_comparison.py
```

追加した variant:

```text
clean_city_terrain_off
street_readability_v1
street_readability_angle_v1
facade_density_road_camera_v2
street_precision_overview_v2
```

追加内容:

- Terrain を baseline 後に OFF にする自動比較。
- 建物ファサードの窓、看板、店舗風パネル密度を増やす `facade_density_v2`。
- 道路が見えやすい低めの road camera。
- 街路樹、車、街灯、信号を道路/歩道沿いに並べる precision street asset 配置。
- EXR / PNG / contact sheet / JSON report の自動生成。

生成物:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_contact_sheet_v5_facade_road_precision.png
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_facade_density_road_camera_v2.png
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_street_precision_overview_v2.png
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/radius100_ue5_compare_report.json
```

検証:

- `python -m py_compile`: OK
- UE5 Python render: OK
- EXR export: OK
- PNG conversion: OK
- Report JSON update: OK
- API cost: none, local UE5 only

注意:

- `-nullrhi` では UE5 5.7 が `EXCEPTION_INT_DIVIDE_BY_ZERO` でクラッシュした。
- 通常レンダー経路では成功したため、現時点では `-nullrhi` を使わない。

目視評価:

- ファサード密度、街灯、車、木の情報量は増えた。
- ただし、まだ実写級ではない。
- 青い抜け/地面の欠落感があり、道路面と地形面の整理が次の主要課題。
- 次は `Road / Sidewalk / GroundPlane` を明示的な連続面として再構成し、建物の足元と接地感を改善する。

## 実装ログ 2026-05-22 追記

目的:

`Road / Sidewalk / GroundPlane` を UE5 側で明示的に作り直し、青い抜けと接地感の弱さを改善する。

追加した variant:

```text
explicit_ground_road_sidewalk_v1
explicit_ground_overview_v1
```

追加内容:

- `ExplicitGround_CityBase`: 都市床の連続ベース面。
- `ExplicitRoad_Main_Asphalt`: 主道路コリドー。
- `ExplicitRoad_Cross_Asphalt`: 交差道路。
- `ExplicitSidewalk_*`: 左右歩道と横断方向歩道。
- `ExplicitCurb_*`: 道路と歩道を分ける縁石。
- `ExplicitLaneDash`, `ExplicitCrosswalkStripe`: 車線・横断歩道。
- `ExplicitPavingTile`: 歩道タイルの反復ディテール。

生成物:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_contact_sheet_v6_explicit_ground.png
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_explicit_ground_road_sidewalk_v1.png
projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_explicit_ground_overview_v1.png
```

検証:

- `python -m py_compile`: OK
- UE5 Python render: OK
- EXR export: OK
- PNG conversion: OK
- Contact sheet generation: OK
- Report JSON update: OK

目視評価:

- 道路、歩道、都市床の面は前回より読みやすくなった。
- 青い抜けは減ったが、広域カメラではまだ一部に残る。
- 次は GroundPlane の範囲とZ高さを微調整し、建物足元の遮蔽と道路接続をさらに詰める。
