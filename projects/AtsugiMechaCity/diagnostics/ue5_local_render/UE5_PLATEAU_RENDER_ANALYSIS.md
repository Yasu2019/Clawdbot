# UE5 / PLATEAU 実写背景化 分析レポート

作成日: 2026-05-21 JST  
対象: `projects/AtsugiMechaCity/diagnostics/ue5_local_render/`  
目的: ローカル環境のみで、UE5 / PLATEAU / PBR都市素材に近い背景レンダーへ引き上げるための現時点の問題点、試行結果、次の改善方針を整理する。

## 結論

UE5 への PLATEAU 実アセット取り込みは成功した。  
ただし、現時点の出力は「実写背景」には未達である。

主因は UE5 の能力不足ではなく、入力している PLATEAU/CityGML 由来の建物が主に箱形状で、実写品質に必要な外壁、窓、店舗、看板、道路表面、街路樹、車両、信号などの高密度 PBR/実写テクスチャを持っていないことにある。

API 消費は行っていない。今回の試行はローカル Blender + ローカル UE5 のみ。

## 現時点の成果物

- 最終プレビュー:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/Atsugi_UE5_plateau_city_real_asset_materialized_view.png`
- 最終 EXR:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/Atsugi_UE5_plateau_city_real_asset_cmscale.exr`
- Blender -> UE5 用 FBX:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx`
- Blender export script:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/export_hon_atsugi_plateau_for_ue5.py`
- UE5 import/render script:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_import_render_plateau_fbx.py`
- Export report:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/hon_atsugi_plateau_ue5_export_report.json`
- UE5 render report:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_import_render_plateau_fbx_report.json`

## 元データの状態

既存 Blender シーン:

- `projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/Hon_Atsugi_Station_Plateau_Mecha.blend`
- サイズ: 約 130MB
- オブジェクト数: 1629
- メッシュ数: 1626
- マテリアル数: 14
- 画像テクスチャ数: 2

既存レポート上の構成:

- 地形:
  - 頂点: 248406
  - 面: 82802
- 道路:
  - 頂点: 11626
  - 面: 10142
- 建物:
  - 元件数: 1583
  - 描画件数: 1541
  - メカ干渉回避でスキップ: 42
- 手続き的ディテール:
  - 道路: 4
  - 歩道: 8
  - 車線破線: 37
  - 横断歩道ストライプ: 25
  - レール: 3
  - 駅前広場: 2
  - 窓パネル: 6604
  - 看板パネル: 25

重要な観察:

- PLATEAU 由来の都市形状は実座標ベースで有用。
- ただし、建物は単純な箱形状が中心。
- Blender シーン内の画像テクスチャはメカ側が中心で、都市背景の実写外壁テクスチャはほぼない。
- そのため、UE5 に持ち込んでも見た目は箱状の都市になる。

## トライ結果

### Trial 1: UE5 procedural city

目的:

UE5 の SceneCapture2D がローカルで安定して画像を吐けるか確認する。

結果:

- 成功。
- 出力:
  - `Atsugi_UE5_procedural_city_color2_view.png`
- 内容:
  - UE5 基本 Cube で道路、ビル、横断歩道、信号、看板、窓帯を生成。
  - Material を `/Game/CodexGenerated` に作成。
  - SceneCapture2D + TextureRenderTarget2D + EXR export が動作。

得られた知見:

- `HighResShot` や Editor viewport スクリーンショットはヘッドレス実行で不安定。
- `SceneCapture2D` + `RenderingLibrary.export_render_target()` は安定。
- UE5 は EXR を出すため、確認用 PNG には FFmpeg 変換が必要。

未達:

- 形状が手作りブロックアウトで、背景が 2D/玩具的に見える。
- 実写感には全く不足。

### Trial 2: Blender PLATEAU scene をそのまま FBX 化

目的:

既存の本厚木 PLATEAU Blender シーンを UE5 へ取り込む。

初期 FBX:

- `Hon_Atsugi_Station_Plateau_UE5.fbx`
- サイズ: 約 93.6MB
- 入力メッシュ数: 1626
- Export 後の主なまとまり:
  - `UE5_HonAtsugi_Terrain`
  - `UE5_HonAtsugi_Infrastructure`
  - `UE5_HonAtsugi_Buildings`
  - `UE5_HonAtsugi_Facades`
  - `UE5_HonAtsugi_Mecha`

結果:

- UE5 import 自体は成功。
- ただし、レンダーは黒背景に近く、画面上部に巨大な断片のみ。

問題:

- メカを含めた FBX の bounds が異常に大きくなった。
- UE5 側の自動カメラフレーミングが壊れた。
- 実座標とメカ由来の大きな境界が混ざり、カメラが意図しない位置へ飛んだ。

### Trial 3: PostProcessVolume property 修正

問題:

UE5.7 で `PostProcessVolume.b_unbound` が見つからず、レンダー直前で Python が停止した。

ログ上のエラー:

```text
PostProcessVolume: Failed to find property 'b_unbound'
```

対策:

- `set_first_existing_property()` を追加。
- `b_unbound`, `unbound`, `is_unbound` の候補を順に試すようにした。

結果:

- この停止要因は解消。

### Trial 4: シーン再センタリング

目的:

PLATEAU 実座標の巨大オフセットを消し、UE5 原点付近で扱えるようにする。

対策:

- Blender export 時に bounds を取得。
- XY 中心と最低 Z を基準に原点へ移動。
- transform を apply。

結果:

- Blender 側 report では再センタリングが成功。
- ただし、メカを含む場合は bounds が依然として異常に大きい。

原因:

- メカ側メッシュまたはその変換情報が都市背景に比べて大きすぎる。
- 背景評価ではメカを含めないほうが安定。

### Trial 5: City-only FBX

目的:

背景品質評価を優先し、メカを除外して PLATEAU 都市だけを UE5 に渡す。

FBX:

- `Hon_Atsugi_Station_Plateau_CityOnly_UE5_Centered.fbx`
- サイズ: 約 3.64MB

Blender report:

- 範囲:
  - X: -591.30m から 591.30m
  - Y: -583.17m から 583.17m
  - Z: 0.0m から 102.09m
- 地形、道路/歩道、建物、窓/看板を保持。

結果:

- UE5 import 成功。
- カメラフレーミングも改善。
- ただし、まだ灰色の箱形状が主体。

### Trial 6: FBX scale 修正

問題:

Blender から UE5 へ渡す際に `global_scale=100.0` を使った結果、UE5 bounds が 100 倍相当になった。

対策:

- `global_scale=1.0` に変更。
- FBX 名を `Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx` に変更。
- UE5 側 import 先も新規パスに変更。

UE5 report:

- bounds origin:
  - `[0.0, 0.0, 5104.3456]`
- bounds extent:
  - `[59129.96875, 58317.00390625, 5104.3536]`

解釈:

- UE5 単位は cm のため、約 591m x 583m x 51m 相当として妥当。
- スケール問題は概ね解消。

### Trial 7: UE5 側 material slot 強制割当

目的:

FBX import 後のマテリアルが灰色に見える問題を軽減する。

実装:

- `apply_plateau_materials()` を追加。
- material slot 名を見て、以下に再割当。
  - terrain
  - building
  - window
  - sign
  - road
  - sidewalk
  - line
  - rail
  - plaza

最終 report 上の割当:

- `HonAtsugi_Building_Grey` -> building
- `HonAtsugi_Dark_Window_Glass` -> window
- `HonAtsugi_Sign_Panels` -> sign
- `HonAtsugi_Road_Asphalt` -> road
- `HonAtsugi_Station_Plaza_Paving` -> plaza
- `HonAtsugi_Enhanced_Asphalt` -> road
- `HonAtsugi_Sidewalk_Concrete` -> sidewalk
- `HonAtsugi_Road_WhiteLine` -> line
- `HonAtsugi_Rail_Steel` -> rail
- `HonAtsugi_Rail_Bed` -> rail
- `HonAtsugi_Terrain_Matte` -> terrain

結果:

- 割当処理は成功。
- ただし、プレビュー上はまだ大半が灰色/黒に見える。

推定原因:

- material slot が正しくても、元の形状とカメラ位置の関係で、窓/看板/道路など細部が見えにくい。
- SceneCapture2D の露出/空/反射/ライトがまだ不足。
- FBX の単一 StaticMesh combine により、マテリアルはあるが細部の視認性が低い。
- そもそも都市形状が単純な箱で、実写的な陰影/凹凸がない。

## 現時点の問題点

### 1. PLATEAU 建物形状が箱に近い

実写感に最も効いている問題。  
PLATEAU は都市の位置、建物高さ、概形には強いが、そのままでは YouTube にあるようなフォトリアル背景にはならない。

不足している要素:

- 実写外壁テクスチャ
- 窓フレームの奥行き
- 店舗ファサード
- 看板の詳細
- エアコン室外機、配管、ベランダ、階段などの付帯物
- 道路の汚れ、白線の摩耗、マンホール、側溝
- 信号、標識、街灯、電柱、電線、車、歩道植栽

### 2. メカを同一 FBX に含めると bounds が壊れる

メカ入り export では bounds が巨大になり、UE5 のカメラが破綻した。  
背景とメカは分離して扱うべき。

推奨:

- 背景: PLATEAU city-only FBX
- メカ: 別アセットとして UE5 へ import
- 合成/配置: UE5 level script で座標を合わせる

### 3. UE5 import 時のスケール管理が重要

Blender m と UE cm の変換で `global_scale=100` を使うと、今回の流れでは過大スケールになった。  
最終的には `global_scale=1.0` が安定した。

### 4. ヘッドレス UE5 のスクリーンショット方式に制約

`HighResShot` や editor viewport 依存は不安定。  
今回安定したのは以下。

- `SceneCapture2D`
- `TextureRenderTarget2D`
- `RenderingLibrary.export_render_target()`
- EXR -> PNG は FFmpeg 変換

### 5. 空/露出/ポストプロセスが未完成

現在の出力は黒背景が強く、空や環境光が弱い。  
簡易 sky backdrop を試したが、カメラに十分入っていない。

必要な改善:

- SkyAtmosphere / DirectionalLight / SkyLight を正規構成で追加
- PostProcess の露出固定
- Auto Exposure の制御
- Camera target と sky backdrop の位置調整
- Lumen/反射設定の実レンダー確認

### 6. UE5 に入っただけでは実写にならない

UE5 は強力なレンダラーだが、入力アセットが単純な箱なら、結果も単純な箱になる。  
フォトリアル化の主戦場はレンダラーではなく、アセット密度、PBR素材、照明、カメラ、ポスト処理である。

## 成功した点

- ローカル UE5 の起動確認。
- SceneCapture2D によるヘッドレス画像出力。
- Blender PLATEAU scene から UE5 向け FBX export。
- 実座標の再センタリング。
- メカ除外による city-only 背景 FBX の安定化。
- UE5 import 成功。
- UE5 側 material slot 再割当成功。
- API 消費なしで完了。

## 未達の点

- 実写品質の背景。
- カラフルで詳細な街路、店舗、看板、信号、道路表面。
- メカと実アセット背景の最終統合。
- 動画化。
- Telegram 送信。

今回の依頼範囲では、まず問題点と試行結果の分析記録を優先したため、動画生成と送信は未実施。

## 次に取るべき方針

### 優先度 A: UE5 背景の最低限の見栄え改善

短期で効果が大きい。

実装候補:

- SkyAtmosphere / ExponentialHeightFog / SkyLight / DirectionalLight を標準構成化。
- PostProcessVolume の露出固定。
- カメラを道路面に近づける。
- city-only mesh を combine せず、地形/道路/建物/窓/看板を別 StaticMesh として import する。
- 道路と建物の material をより強く差別化する。

### 優先度 B: PBR 都市素材の導入

実写感に最も効く。

無料/ローカル寄りの候補:

- 既存 `data/workspace/apps/blender_assets/ambientcg` の活用
- Poly Haven / ambientCG などの CC0 PBR 素材をローカル保存して使う
- 道路、コンクリート、ガラス、タイル、金属、看板発光マテリアルを UE5 material として標準化

### 優先度 C: PLATEAU + 装飾アセットのハイブリッド

PLATEAU は地理的正確性、装飾はフォトリアル性として役割分担する。

追加すべき装飾:

- 低ポリ車両
- 信号
- 標識
- 街灯
- 電柱/電線
- 街路樹
- 自販機
- 店舗看板
- ガードレール
- マンホール
- 道路汚れデカール

### 優先度 D: メカ統合

背景が安定してから実施する。

方針:

- 背景 FBX とメカ FBX/UE asset を分離。
- メカは既存テクスチャを保持。
- UE5 level script で高さ合わせ。
- カメラごとにメカ位置を確認。

## 推奨する次回作業単位

1. `ue5_import_render_plateau_fbx.py` を「背景メッシュを分割 import」へ修正。
2. SkyAtmosphere / exposure / fog を追加。
3. 道路面が見えるローアングルカメラを 2 パターン作る。
4. PBR material を road/building/window/sign に適用。
5. プレビュー PNG を比較。
6. 合格後にメカを別 import して統合。
7. 動画化。
8. Telegram 送信。

## 判断

現時点の UE5/PLATEAU フローは「採用候補」だが、まだ完成フローではない。  
採用判断としては `ADOPT_PARTIAL` が妥当。

理由:

- ローカルで実アセットを UE5 に持ち込めることは確認済み。
- ただし、見た目品質は Blender/手続きレンダーの過去成果をまだ上回っていない。
- 実写感には、PLATEAU の箱形状を補完する PBR素材と装飾アセットが必須。

## 記録すべき教訓

- UE5 を使えば自動的に実写になるわけではない。
- 実写感は、レンダラーよりもアセット密度と素材品質に強く依存する。
- PLATEAU は都市配置の土台として有用だが、そのまま背景完成品にはならない。
- メカと背景は同一 FBX にまとめない。
- Blender -> UE5 では座標、スケール、bounds を必ず report 化する。
- ヘッドレス UE5 は SceneCapture2D を標準とする。
- 失敗時は単純リトライせず、ログを見て原因を修正してから再試行する。

## 追加アドバイス反映: ミニPC向け動画生成方針

参照元:

- `C:\Users\yasu\Downloads\UE5_MINIPC_VIDEO_ADVICE_20260521.md`
- プロジェクト内保存先:
  - `projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_MINIPC_VIDEO_GENERATION_ADVICE.md`

この外部アドバイスは、本レポートの結論と整合している。特に重要なのは、UE5 を「自動実写化ツール」として扱わず、Blender で整理した軽量アセット、PLATEAU 位置情報、PBR 素材、装飾アセットを UE5 で静的にレンダーする構成へ寄せる点である。

### 反映すべき追加判断

- 採用判断は引き続き `ADOPT_PARTIAL`。
- ミニPCでは、いきなり高品質動画を狙わない。
- まず 1280x720 の静止画比較を行う。
- 合格後に 5秒 / 24fps / 120フレームの短尺連番へ進む。
- 10秒、15秒、1920x1080、複数カメラは後段に回す。

### ミニPC向けの制約

避けるべき初期条件:

- UE5 リアルタイム高品質動画
- Lumen 高品質
- Nanite 大量都市
- 広域 PLATEAU 都市全体の高密度レンダー
- 4K 動画
- メカ、都市、PBR、群衆、車両、エフェクトを同時投入

初期目標:

- 1280x720 または 1920x1080 の短いカット
- 5秒から15秒
- 1カメラ固定、またはゆっくりしたドリー
- 背景範囲は駅前/道路1区画だけ
- メカは背景と別アセット
- UE5 は静止画連番または低負荷動画出力に使う

### 追加された必須方針

1. メカと背景を同一 FBX にまとめない。
2. city-only 背景を `Terrain / Road / Sidewalk / Buildings / Windows / Signs / Rails / Props` に分割する。
3. Blender export 時に bounds JSON report を必ず出す。
4. UE5 import 時に bounds、material slot、camera target を report 化する。
5. SceneCapture2D + RenderTarget + EXR export を標準レンダー方式にする。
6. HighResShot や Editor viewport 依存は使わない。
7. まず静止画比較を行い、合格後に 5秒動画化する。
8. 最初の対象範囲は半径100mに制限する。
9. Lumen / Nanite / 高品質影は初期段階では使わない。
10. PBR 素材は道路、歩道、建物、窓、看板の順に適用する。

### 次回実装候補ファイル

アドバイスでは以下の実装単位が推奨されている。

- `scripts/blender/export_city_split_for_ue5.py`
- `scripts/ue5/import_city_split_render.py`
- `scripts/ue5/setup_lighting_postprocess.py`
- `scripts/ue5/apply_pbr_materials.py`
- `scripts/ue5/render_still_and_frame_sequence.py`
- `config/ue5_minipc_render_profile.json`
- `docs/UE5_MINIPC_PIPELINE.md`
- `reports/render_comparison_template.md`

既存構成との整合を取る場合、最初は `projects/AtsugiMechaCity/diagnostics/ue5_local_render/` 配下へ試験実装し、安定後に scripts/docs へ昇格するのが安全である。

### 最初のテスト条件

- 半径100mの city-only 背景
- メカなし
- ローアングルカメラ
- SkyAtmosphere / DirectionalLight / SkyLight / ExponentialHeightFog / PostProcessVolume あり
- 1280x720 静止画
- 3パターン出力:
  1. baseline
  2. pbr_road
  3. pbr_road_building_props

### 合格条件

- 黒背景にならない。
- カメラが都市を正しく捉える。
- 道路面が見える。
- 建物が灰色一色ではない。
- logs/report に bounds 異常がない。
- PNG を人間が比較できる。

### やってはいけないこと

- PLATEAU 広域全体を一気に高品質化しようとする。
- メカと都市を同じ FBX にまとめる。
- UE5 に入れれば自動的に実写になると考える。
- いきなり動画を出そうとする。
- 失敗画像だけ見てログを見ない。
- Lumen / Nanite / 高品質影を最初から全部 ON にする。
- 灰色の箱のままカメラだけ変えて粘る。
- 1つの巨大 StaticMesh に combine して素材調整不能にする。
- PBR なしで実写感を求める。
- 遠景まで全部作り込む。

### 更新後の優先順位

最優先:

- 背景とメカを完全分離する。
- city-only を分割 export する。
- 半径100mのテストシーンを作る。
- Sky / Light / Fog / PostProcess を標準化する。
- SceneCapture2D 出力テンプレートを作る。
- 道路 PBR を適用する。
- ローアングルカメラを追加する。

次点:

- 建物 PBR を適用する。
- 窓ガラス material を改善する。
- 看板 emissive を追加する。
- 信号 / 街灯 / 車 / 電柱を低ポリ追加する。
- 5秒連番をレンダーする。
- FFmpeg で mp4 化する。

その後:

- メカを別 import する。
- 接地調整する。
- 15秒動画化する。
- 1920x1080化する。
- 複数カメラ化する。
- Telegram 送信する。
- Portal カード化する。

## 2026-05-21 半径100m / 分割 / 1280x720 比較テスト結果

実装ファイル:

- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/export_city_split_radius100_for_ue5.py`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_radius100_comparison.py`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/config_ue5_minipc_render_profile.json`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare_template.md`

出力:

- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/radius100_split/radius100_split_export_report.json`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/radius100_ue5_compare_report.json`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_baseline.png`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_pbr_road.png`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_pbr_road_building_props.png`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_contact_sheet.png`

実施内容:

- Blender 側で半径100m中心の city-only 背景をカテゴリ分割した。
- 分割カテゴリは `Terrain / Road / RoadMarkings / Sidewalk / Buildings / Windows / Signs / Rails`。
- UE5 側でカテゴリ別 FBX を import した。
- 1280x720 の静止画を `baseline / pbr_road / pbr_road_building_props` の3パターンで出力した。
- SceneCapture2D + RenderTarget + EXR export を使用した。
- EXR は FFmpeg で PNG に変換した。
- 比較用 contact sheet を作成した。

結果:

- パイプラインは end-to-end で成功。
- API 消費なし。
- 黒背景問題は、明示 sky backdrop により改善。
- カメラが道路下に入る問題は、地形最低Zではなく道路/歩道 bounds を使うことで改善。
- `Signs` は半径100m範囲内に有効 face がなく、FBX未出力。
- 最終画像は、まだ実写品質には未達。

残る問題:

- PLATEAU 建物が箱形状で、ファサード密度が低い。
- 前景道路 proxy により道路の存在は見えるが、構図としてはまだ弱い。
- 右側の大きな建物が画面を塞ぎ、街路の奥行きが見えにくい。
- PBR道路テクスチャの効果が弱い。
- 信号/車/街灯などの低ポリ props は追加されたが、画面内で小さすぎる。

次の一手:

- 動画化には進まず、静止画改善を継続する。
- カメラターゲットを道路中心へさらに寄せる。
- 右端を塞ぐ建物を一時的に非表示、またはカメラ位置を変更する。
- 前景道路の角度と位置をカメラに合わせて調整する。
- props を近景に大きく配置する。
- asphalt / sidewalk / building のコントラストを強くする。

## 2026-05-21 構図改善 v2

実施内容:

- 追加バックアップブランチを作成し GitHub に push:
  - `backup/ue5-radius100-composition-before-20260521-100841`
- `ue5_render_radius100_comparison.py` を更新。
- カメラを道路面基準で再配置。
- PLATEAU の巨大 `Windows` actor を最終比較では非表示化。
- 近景の補強用 proxy を追加:
  - 前景アスファルト面
  - 車線破線
  - 横断歩道ストリップ
  - 歩道縁石
  - 左右の簡易ファサード
  - 窓パネル
  - 車
  - 信号/街灯/看板
- 既存の 3枚比較ループは維持:
  - `baseline`
  - `pbr_road`
  - `pbr_road_building_props`

出力:

- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_pbr_road_building_props.png`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/r100_contact_sheet.png`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/radius100_ue5_compare_report.json`

結果:

- 1280x720 の3枚比較は成功。
- API 消費なし。
- 黒背景問題は解消傾向。
- 道路面、車線、建物面、近景 props が見えるようになった。
- 前回の「青い壁と線だけ」の画より、街路構図として比較可能になった。

未達:

- まだ実写品質ではない。
- 道路面がPBRらしく見えるには、テクスチャスケールと色調整が必要。
- 建物ファサードはまだ単純な板で、実写外壁の密度が足りない。
- props は見えるが、信号色、看板文字、車形状は簡易すぎる。

次の推奨:

- まだ動画化しない。
- 次も同じ静止画3枚比較で、proxy ファサードへ PBR wall/tiles texture を適用する。
- 信号灯を赤黄緑の emissive 小面で追加する。
- 看板に TextRender を追加する。
- 車を cube からもう少し車らしい低ポリ形状へ分割する。
- asphalt texture の tiling/UV 問題を避けるため、UE material ではなく Blender 側で前景道路専用 mesh/UV を作ることも検討する。
