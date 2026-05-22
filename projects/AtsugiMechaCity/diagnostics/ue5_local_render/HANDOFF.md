# HANDOFF: AtsugiMechaCity UE5 LOD2 Building Import
更新: 2026-05-22 21:35 (v37完了 / Gemini 3.5引継ぎ用)

---

## プロジェクト概要

**目標**: 本厚木駅周辺の PLATEAU CityGML LOD2（外壁テクスチャ付き実建物）を UE5 に恒久インポートし、  
フローティングスラブ（sky-blocker）を本物の建物メッシュで置き換えて都市景観のリアリティを向上させる。

**UE5 プロジェクト**: `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\AtsugiMechaCity.uproject`  
**PLATEAU データ**: `D:\Clawdbot_Docker_20260125\data\PLATEAU\Atsugi\udx\bldg\`  
**作業ディレクトリ**: `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render\`

---

## 現在の状態（v37 / 2026-05-22 21:30 時点）

### 動作している機能
- PLATEAU LOD2 FBX の UE5 インポート＋テクスチャ適用
- 3 カメラセット（sealed / overview / road）のレンダリング
- sky-blocker スラブ（peripheral_building_walls）との共存
- LOD2 z-offset 自動整合（surface_z 基準）
- Telegram への PNG 自動送信

### 最新出力ファイル（`radius100_compare/`）
| ファイル | 内容 |
|---------|------|
| `r100_lod2_sealed_v35.png` | 街路レベル・FOV38°・空なし・LOD2建物背景 |
| `r100_lod2_overview_v35.png` | 高度 150m 俯瞰・建物群全体可視（v36 で大改善） |
| `r100_lod2_road_v35.png` | 道路面＋左右LOD2建物・空なし（v37 で修正） |
| `r100_lod2_contact_v37.png` | 3 枚並べたコンタクトシート |

### 残る改善余地（現時点の「ダメ」な点）
1. **道路色が明るいベージュ** → 暗いアスファルトに見えない（ライティングが強すぎ）
2. **proxy buildings が白くてゲームっぽい** → `spawn_proxy_buildings()` などのスラブ建物の材料
3. **全体的に過露出** → sun intensity=9.0 が強すぎる可能性
4. **sealed_view の建物が近くて圧迫感** → FOV または camera Z をさらに調整余地あり

---

## ファイル構成

```
diagnostics/ue5_local_render/
├── plateau_lod2_extract.py          # PLATEAU GML → JSON 抽出
├── plateau_lod2_to_fbx.py           # JSON → FBX（Blender headless）
├── plateau_lod2_radius100.json      # 抽出結果: 25棟, 991面, 25テクスチャ
├── plateau_lod2_buildings_radius100.fbx   # FBX（476KB）
├── plateau_lod2_buildings_radius100.fbm/  # テクスチャ 64 JPGs
├── ue5_render_radius100_comparison.py     # メイン UE5 スクリプト
├── HANDOFF.md                        # 本ファイル
└── radius100_compare/                # EXR / PNG 出力先
```

---

## 座標系（必読）

| 系 | 原点 | 単位 | 変換 |
|----|------|------|------|
| CityGML | EPSG:6697 (lat/lon) | 度 | pyproj で 6697→6677 |
| Blender | 本厚木駅中心 | m | Transformer.from_crs(6697,6677,always_xy=False) |
| UE5 world | FBX spawn origin（road_origin付近） | cm | Blender と同じ原点(0,0,0) にスポーン |
| road_origin | PLATEAU Road mesh の bounds center | cm | 実行時に自動計算 |

### Y 軸反転（最重要）
FBX エクスポート設定 `axis_forward="-Y"` により **Blender +Y = UE5 -Y**（符号反転）。

- sealed camera は UE5 座標 `road_origin + (-1800, -6400, 450)` cm
- これを Blender 座標に直すと `(-18m, +64m)` → **Y 符号が逆**
- `plateau_lod2_extract.py` の `CAMERA_EXCLUDE_CENTER = (-18.0, +64.0)` は正の +64（間違えると全画面グレーになる）

### LOD2 の z 座標（海抜）
- LOD2 の z は**海抜メートル**。本厚木駅周辺は海抜 17–19m。
- Blender ではそのまま m 単位で出力 → FBX 経由で UE5 では cm 単位（1m=100cm）
- UE5 内で `lod2_min_z` は実測 ≈ −171cm（地面スラブ除外後の最低頂点）
- `lod2_z_offset = surface_z − lod2_min_z ≈ 1921 − (−171) = 2092cm` を適用して道路面に整合

---

## バージョン別実施履歴とトラブル

### Phase 1: 空削減（〜v27）
**目標**: 街路レベルカメラで空が映る割合を 30% → 10% 以下に

| バージョン | 変更 | 結果 |
|-----------|------|------|
| v13 | baseline | 空 ≈30% |
| v26 | カメラ高度 800cm | 俯瞰になりすぎ NG |
| v27 | カメラ高度 450cm, FOV=26° | **空 ≈10% 達成。v27 を Phase1 最終確定** |

**Telegram 送信トラブル**:
- 日本語キャプションで `Bad Request: strings must be encoded in UTF-8` → **ASCII のみに変更**
- 3.9MB PNG で exit code 55 → `ffmpeg -vf scale=iw/2:ih/2` で縮小して解決

---

### Phase 2: LOD2 建物インポート（v28〜v37）

#### v28〜v33: カメラ内部インシデント（全画面グレー）

**症状**: sealed_view / road_view が完全グレー

**根本原因（Y 軸反転バグ）**:

```
誤認: カメラ位置 UE5 y=-6400cm → Blender y=-64m
正解: カメラ位置 UE5 y=-6400cm → Blender y=+64m（axis_forward="-Y" で符号反転）
```

カメラ除外ゾーン中心を `(-18.0, -64.0)` と設定していたため、除外すべき建物を除外できず、
カメラが LOD2 建物の内部に入って全画面グレーになっていた。

**対策履歴**:

| バージョン | 試みた対策 | 結果 |
|-----------|-----------|------|
| v28 | LOD2 FBX 初回インポート | グレー（Y バグ未発覚） |
| v29 | CAMERA_EXCLUDE_RADIUS = 50m, center=(-18,-64) | グレー継続 |
| v30 | 地面スラブ除外（z<1m）追加 | グレー継続（Y バグ残存） |
| v31 | EXCLUDE_RADIUS = 80m + BB コンテインメント追加 | UnboundLocalError `surface_z` が発生 |
| v31 修正 | z-offset 適用を surface_z 計算後に移動 | グレー継続（Y バグ残存） |
| v34 | **CAMERA_EXCLUDE_CENTER = (-18.0, +64.0) に修正** | **成功！建物テクスチャ表示** |

**v31 の UnboundLocalError 詳細**:
```python
# NG: lod2_z_offset 計算が surface_z 計算より前にあった
lod2_z_offset = surface_z - lod2_min_z   # ← surface_z がまだ未定義

# 修正: lod2 bounds 取得（import後すぐ）と z-offset 適用（surface_z計算後）に分離
```

---

#### v34: 初回成功

**結果**:
- sealed_v34: LOD2 青タイル建物が背景に表示
- overview_v34: 建物ファサードテクスチャ確認（ただし camera が壁に近すぎ）
- road_v34: フォトリアルな建物ファサードが背景に可視

**v34 時点の設定**:
- `CAMERA_EXCLUDE_CENTER = (-18.0, +64.0)`, radius=80m
- `lod2_z_offset ≈ 2092cm`（surface_z=1921, lod2_min_z=−171）
- `import_lod2_buildings()` はキャッシュ再利用に修正済み

---

#### v35: 改善試行（3 カメラ専用セット追加）

**変更**:
- Sidewalk material: `road_patch`(暗) → `sidewalk`(明)
- road_camera FOV: 50° → 35°（絞りすぎ）
- overview camera Z: +1250 → +2500cm（不十分）
- sealed FOV: 26° → 38°
- north_sky_specs に 8 スラブ追加（うち2つが road_camera 視野を封鎖）
- `lod2_sealed_v35`, `lod2_overview_v35`, `lod2_road_v35` の 3 EXR 追加

**トラブル**:

| 症状 | 原因 | 対策 |
|------|------|------|
| road_v35 が完全な砂色の壁 | `(600,-1500)` スラブが road_camera 視野を封鎖 | 問題スラブを削除（v36） |
| overview_v35 が建物の壁のアップ | Z=2500cm（25m）では LOD2 建物 z_max=102m に対して低すぎ | Z=15000cm（150m）に変更（v36） |
| sealed_v35 は若干改善 | FOV38° で奥行き表現が改善 | そのまま維持 |

---

#### v36: overview 大改善、road は未解決

**変更**:
- `(-600,-1500)` と `(600,-1500)` の問題スラブを削除
- overview Z: +2500 → +15000cm（建物 z_max=102m を超える 150m 俯瞰）
- overview FOV: 52° → 68°

**結果**:
- overview_v35: **建物群全体が俯瞰で見える（大幅改善）**
- road_v35: まだ砂色の壁（別の原因が残存）

**road が砂色の壁になった原因の再分析**:
```
road_camera_loc = road_origin + (-2450, -6550, 800)cm
→ Blender 座標: (-24.5m, +65.5m)
→ カメラ除外ゾーン中心 (-18m, +64m) から距離 ≈ 6.5m（ゾーン内なので LOD2 建物はなし）
→ 付近の proxy buildings / sky-blocker スラブが FOV46° の視野を塞いでいた可能性
```

---

#### v37: road 完全修正

**根本対策**: road_camera XY を sealed_camera と同一（除外ゾーン中心）に変更

```python
# v37 road_v35 camera 設定
road_v35_loc    = road_origin + (-1800, -6400, +1200)  # Z=12m
road_v35_target = road_origin + (-400, -2600, +300)    # sealed_camera と同じターゲット
FOV = 50°
```

**結果**: 道路面＋左右の LOD2 建物（青タイル）が両方見えるビューが完成

---

## 現在のスクリプト設定（v37 確定版）

### `plateau_lod2_extract.py`
```python
RADIUS_M               = 100.0
MARGIN_M               = 20.0
CAMERA_EXCLUDE_CENTER  = (-18.0, +64.0)   # ★ +64（負にしない）
CAMERA_EXCLUDE_RADIUS  = 80.0
CAMERA_Z               = 23.7
# 地面スラブ除外
if max(v[2] for v in verts) < 1.0:
    return None
```

### `plateau_lod2_to_fbx.py`
```python
bpy.ops.export_scene.fbx(
    filepath=str(FBX_OUT),
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Y",      # ★ UE5 に合わせた軸設定
    axis_up="Z",
    path_mode="COPY",       # テクスチャを .fbm/ にコピー
    embed_textures=False,
    bake_anim=False,
)
```

### `ue5_render_radius100_comparison.py` キーポイント
```python
# --- import_lod2_buildings() ---
# キャッシュ再利用（v34 以降）
existing = load_asset(LOD2_DEST + "/LOD2_Buildings")
if existing is not None:
    actor = spawn_actor_from_object(existing, Vector(0,0,0))
    return existing, actor

# --- z-offset（main() 内、surface_z 計算後）---
lod2_z_offset = surface_z - lod2_min_z
lod2_actor.set_actor_location(Vector(road_origin.x, road_origin.y, lod2_z_offset))

# --- v35 カメラ設定（3 カメラ） ---
# sealed_v35: FOV=38°, Z=+450cm, 同 sealed_camera_loc
# overview_v35: Z=+15000cm（150m）, FOV=68°
# road_v35: XY=sealed_camera_loc, Z=+1200cm, FOV=50°

# --- Sidewalk material（v35 以降）---
("Sidewalk", "sidewalk")   # 明るいコンクリート（旧: "road_patch" = 暗）

# --- sealed camera ---
sealed_camera_loc = road_origin + (-1800, -6400, +450)  # FOV=38°
```

---

## 次のステップ提案（優先順）

### 1. ライティング改善（最優先）
道路が明るいベージュに見える原因はライティングが強すぎること。

```python
# setup_lighting() 内
sun.get_component_by_class(DirectionalLightComponent).set_editor_property("intensity", 5.0)  # 現: 9.0
sky.get_component_by_class(SkyLightComponent).set_editor_property("intensity", 1.8)           # 現: 2.8
```

### 2. 道路アスファルト感の強化
現在 road material = `(0.010, 0.011, 0.012)` で設定は暗いが、過露出で飛んでいる。  
PostProcessVolume に Exposure Compensation を追加する方法もある。

```python
# PostProcess に露出補正追加
pp_comp = unreal.MaterialEditingLibrary.create_material_expression(mat, ...)
# または Console command で
unreal.SystemLibrary.execute_console_command(world, "r.EyeAdaptation.ExposureCompensation -1.5")
```

### 3. LOD2 半径拡大（建物密度向上）
`plateau_lod2_extract.py` の `RADIUS_M = 100.0` を 150 or 200 に変更し、  
Blender で FBX を再生成 → UE5 で再インポート。

### 4. sky-blocker スラブの段階的削減
LOD2 建物が十分な背景を提供しているなら、`spawn_peripheral_building_walls()` 内の  
`north_sky_specs` / `back_slabs` を削減して「よりリアルな建物密度」に近づける。

### 5. proxy_buildings / facade_density スラブの改善
`spawn_proxy_buildings()`, `spawn_facade_density_v2()` で生成した建物スラブは  
均一色で「ゲームっぽい」。詳細なテクスチャマテリアルを適用するか、  
LOD2 建物が視野に入る分を非表示にすることで改善できる。

---

## 実行コマンド（再掲）

```powershell
# 1. LOD2 抽出（変更時のみ）
cd D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render
python plateau_lod2_extract.py

# 2. FBX 再生成（extract 変更時のみ）
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python plateau_lod2_to_fbx.py

# 3. UE5 実行
$ue5  = "D:\UnrealEngine\UE_5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe"
$proj = "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\AtsugiMechaCity.uproject"
$scr  = "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render\ue5_render_radius100_comparison.py"
Start-Process $ue5 -ArgumentList "$proj","-unattended","-nop4","-nosplash","-ExecutePythonScript=`"$scr`"" -WindowStyle Minimized

# 4. EXR → PNG 変換（UE5 完了後）
$od = "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render\radius100_compare"
foreach ($v in @("sealed","overview","road")) {
    ffmpeg -y -i "$od\r100_lod2_${v}_v35.exr" -vf "eq=gamma=0.9:contrast=1.0" "$od\r100_lod2_${v}_v35.png"
}

# 5. Telegram 送信（caption は ASCII only）
$TOKEN   = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
$CHAT_ID = "8173025084"
curl.exe -s -X POST "https://api.telegram.org/bot${TOKEN}/sendPhoto" `
  -F "chat_id=${CHAT_ID}" `
  -F "caption=v37 road - LOD2 buildings both sides" `
  -F "photo=@${od}\r100_lod2_road_v35.png"
```

---

## トラブルシューティング早見表

| 症状 | 原因 | 確認コマンド / 対処 |
|------|------|-------------------|
| sealed_view が完全グレー | カメラが LOD2 建物内部に入っている | `CAMERA_EXCLUDE_CENTER` の Y 符号を確認（+64 が正解） |
| `UnboundLocalError: surface_z` | LOD2 z-offset コードが surface_z 計算より前にある | z-offset 適用を `road_origin` 計算の後に移動 |
| road_view が砂色の壁 | sky-blocker スラブが road_camera 視野を封鎖 | スラブの XY が `road_camera_loc` 方向にないか確認 |
| overview が建物の壁アップ | カメラ高度が LOD2 最大建物高（102m=10200cm）以下 | overview Z を `surface_z + 15000` 以上に設定 |
| Telegram 送信エラー 400 | caption に日本語が含まれる | caption を ASCII のみに変更 |
| Telegram 送信エラー 55 | PNG が大きすぎる（>5MB） | `ffmpeg -vf scale=iw/2:ih/2` で縮小 |
| FBX インポートで建物位置がズレる | `lod2_z_offset` が未適用 or `set_actor_location` の XY がずれ | `road_origin.x, road_origin.y, lod2_z_offset` を確認 |
