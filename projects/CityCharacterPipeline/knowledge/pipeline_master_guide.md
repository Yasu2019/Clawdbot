# CityCharacterPipeline マスターガイド
# 生成: 2026-05-17 | 対象Blender: 5.1.1 | 対象OS: Windows 11

> **目的**: AIでなくても同じクオリティの画像・動画を再現できるように、
> すべてのパラメータ・教訓・QC工程・FMEAを記録する。

---

## 1. パイプライン概要

```
YAMLコンフィグ
    ↓ [1/6] QC工程表・FMEA事前分析
    ↓ [2/6] Config検証（必須フィールド確認）
    ↓ [3/6] Blenderスクリプト自動生成
    ↓ [4/6] Blender 5.1 実行（背景読み込み + FBXインポート + レンダー）
    ↓ [5/6] QAゲート（4項目自動スコアリング）
    ↓ [6/6] 知識記録（DB + MD + ByteRover）
```

**実行コマンド**:
```powershell
# 静止画
python run_pipeline.py --config configs/hon_atsugi_dom.yaml

# 動画（静止画合格後）
python run_pipeline.py --config configs/hon_atsugi_dom.yaml --animate

# テスト（Blender実行なし）
python run_pipeline.py --config configs/hon_atsugi_dom.yaml --dry-run --skip-qa
```

---

## 2. 利用可能な3Dモデル（FLBフォルダ）

| モデル名 | FBXファイル | 公式全高(m) | 備考 |
|---|---|---|---|
| DOM | DOM_RIG_Mixamo.fbx | 18.6 | MS-09 Dom |
| GM | GM_Rigged.fbx | 18.0 | RGM-79 |
| Zaku | Zaku_Rig_mixamo.fbx | 17.5 | MS-06F |
| GanCannon | GanCannon_Rig_mixamo.fbx | 17.9 | RX-77 |
| Gelgoog | Gelgoog_Rig_mixamo.fbx | 19.2 | MS-14 |
| Gogg | Gogg_Rig_mixamo.fbx | 17.5 | MSM-03 |
| Gouf | Gouf_Rigged.fbx | 18.7 | MS-07 |
| RickDias | RickDias__Rig_mixamo.fbx | 20.0 | RMS-099 |
| ZGok | ZGok_Rig_mixamo.fbx | 18.4 | MSM-07 |

**場所**: `D:\Clawdbot_Docker_20260125\Gundam\FLB\`

> **重要**: FBXをimport後は `normalize_character()` でスケール調整必須。
> Blenderデフォルト単位ではFBXは非常に小さい（~0.017 Blender unit/m）。

---

## 3. Blender 5.1 互換性対応（必須知識）

### 3.1 Nishita Skyの名称変更
```python
# Blender 4.x まで
sky.sky_type = "NISHITA"

# Blender 5.1 では → MULTIPLE_SCATTERING に変更
# 対応コード（フォールバック方式）:
for _sky_type in ("NISHITA", "MULTIPLE_SCATTERING", "HOSEK_WILKIE"):
    try:
        sky.sky_type = _sky_type
        break
    except TypeError:
        continue
```

### 3.2 非推奨警告（Blender 6.0で削除予定・現時点は動作する）
```
DeprecationWarning: 'World.use_nodes' is expected to be removed in Blender 6.0
DeprecationWarning: 'Material.use_nodes' is expected to be removed in Blender 6.0
```
→ 現時点は無視してよい。Blender 6.0移行時に `bpy.context.scene.world.node_tree` 直接アクセスに変更。

---

## 4. BBox計算の正しい方法（mixamo_action_preview.py 由来）

### NG: Armatureオブジェクトのbound_box
```python
# Armatureはbound_boxが常に空 → height=0になる
bb = armature.bound_box  # ← 使ってはいけない
```

### OK: 子Meshをdepsgraph評価済みで取得
```python
def _bounds_for_objects(objects, use_depsgraph=True):
    depsgraph = bpy.context.evaluated_depsgraph_get() if use_depsgraph else None
    min_v = mathutils.Vector((1e9, 1e9, 1e9))
    max_v = mathutils.Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        src = obj.evaluated_get(depsgraph) if depsgraph else obj
        for corner in src.bound_box:
            world = src.matrix_world @ mathutils.Vector(corner)
            for i in range(3): ...
    return min_v, max_v

# 使い方
meshes = [o for o in armature.children_recursive if o.type == "MESH"]
min_v, max_v = _bounds_for_objects(meshes, use_depsgraph=True)
height = max_v.z - min_v.z
```

---

## 5. カメラ自動配置の公式

```
character_height = 実測高さ（BBox）or 公式全高テーブル
camera_distance  = character_height * 2.5   (85mm望遠相当)
camera_z         = foot_z + character_height * 0.35
target_z         = foot_z + character_height * 0.55  (腰〜胸あたりを注視)
```

**ortho_scale方式（mixamo_action_preview.py）**:
```python
camera.data.type = "ORTHO"
camera.data.ortho_scale = max(float(size.z) * 1.8, 30.0)
camera.location = (cx + 24, cy - 38, cz + 8)
```

---

## 6. マテリアル強化の注意点

### キャラクター子Meshを除外する（重要）
```python
# キャラクター子Meshを収集
char_mesh_ids = set()
for scene_obj in bpy.context.scene.objects:
    if scene_obj.type == "ARMATURE":
        for child in scene_obj.children_recursive:
            char_mesh_ids.add(child.name)

# 建物PBR適用時にスキップ
for obj in bpy.context.scene.objects:
    if obj.name in char_mesh_ids:
        continue  # キャラクターは除外
    # ... PBR適用
```

> **失敗事例**: この除外なしではGMにConcreteテクスチャが適用されて
> ロボットがコンクリート色になった（2026-05-17 確認）。

---

## 7. ライティング設定（本厚木・午後2時）

```yaml
lighting:
  sun:
    lat: 35.4437
    lon: 139.4130
    hour: 14
    energy: 6.0        # 推奨: 5.0〜8.0
  fill_lights:
    - type: "AREA"
      position: [-15, -20, 10]
      energy: 300
      color: [0.95, 0.97, 1.0]   # 空気光（青白）
    - type: "AREA"
      position: [15, -10, 5]
      energy: 150
      color: [1.0, 0.95, 0.88]   # 反射光（暖色）
```

**太陽仰角計算**:
```python
def _sun_elevation(lat, lon, hour):
    # 時角（15度/時間）
    hour_angle = math.radians((hour - 12) * 15)
    lat_r = math.radians(lat)
    # 春分(declination=0)近似
    sin_elev = (math.sin(lat_r) * math.cos(0) +
                math.cos(lat_r) * math.cos(0) * math.cos(hour_angle))
    return math.degrees(math.asin(max(-1, min(1, sin_elev))))
```

---

## 8. 接地AO（ShadowCatcher）設定

```yaml
contact_ao:
  enabled: true
  radius: 4.0      # AOシャドウ半径(m) → キャラ全高/4 が目安
  strength: 0.7    # 0.5〜0.8推奨
  shadow_catcher: true
```

```python
# ShadowCatcherプレーン配置
ao_plane.is_shadow_catcher = True  # Cycles専用
# 足元スポットライト（接地影強調）
spot.data.energy    = 50.0
spot.data.spot_size = math.radians(60)
spot.rotation_euler = Euler((math.radians(180), 0, 0), "XYZ")  # 真下照射
```

---

## 9. QA評価基準

| 項目 | 5点 | 3点（最低合格） | 1点 |
|---|---|---|---|
| material_realism | PBRテクスチャ全適用・写実的 | 一部PBR、一部デフォルト | 全白箱 |
| lighting | 自然光・影・ハイライト調和 | 基本照明あり・深度感不足 | 全黒/全白 |
| camera | 被写体中央・適切な遠近感 | 被写体映るが構図に難 | 被写体なし |
| character_integration | 自然な接地・影あり | 浮いて見える | 不自然・完全ミスマッチ |

**合格条件**: 全項目 >= 3/5

---

## 10. FMEA 高RPNリスクと対策

| RPN | 工程 | 故障モード | 原因 | 対策 |
|---|---|---|---|---|
| **96** | マテリアル | 白箱未適用 | ambientCGアセット不在 | 実行前にアセット確認・fallback Principled |
| **84** | ライティング | フラット照明 | HDRI/太陽未設定 | Nishita Sky + sun_energy>=5 + fill2灯 |
| **81** | 接地AO | DOM浮き | embed_depth不足 | embed_depth=0.75固定 + ShadowCatcher必須 |
| **72** | マテリアル | キャラにPBR適用 | 子Mesh除外なし | char_mesh_ids set で除外（2026-05-17修正）|
| **40** | レンダリング | 全黒フレーム | Emission未接続 | samples>=64 + visual_qa gate |

---

## 11. 3Dマップデータソース選定

| 用途 | データソース | 対応範囲 | 取得方法 |
|---|---|---|---|
| 日本主要都市 | PLATEAU（国土交通省） | 230+都市 | https://plateau.mlit.go.jp/ |
| 全世界（汎用） | OpenStreetMap + Overpass API | 全世界 | `overpy`でクエリ → Blender bmesh押し出し |
| 地形 | SRTM 30m / ALOS | 全世界 | OpenTopography API |
| **禁止** | Google Maps/Earth 3D | — | 利用規約違反（データ抽出不可） |

**YAML config での指定**:
```yaml
terrain:
  data_source: "plateau"    # "plateau" | "osm" | "blend_only"
  plateau_gml_dir: "D:/..."  # PLATEAUあり
  osm_bbox_margin_m: 500    # OSMフォールバック取得範囲
```

---

## 12. 既存参照実装

| 機能 | ファイル | 関数/行 |
|---|---|---|
| BBox計算（正） | `projects/AtsugiMechaCity/mixamo_action_preview.py` | `bounds_for_objects()` L90-101 |
| キャラ正規化 | `projects/AtsugiMechaCity/mixamo_action_preview.py` | `normalize_character()` L104-117 |
| カメラ設定 | `projects/AtsugiMechaCity/mixamo_action_preview.py` | `setup_scene()` L154-187 |
| Mixamoアクション | `projects/AtsugiMechaCity/dom_mixamo_walk_preview.py` | `normalize_target()` |
| 接地処理 | `projects/AtsugiMechaCity/mixamo_action_preview.py` | `lock_to_ground()` L190-194 |

---

## 13. ambientCG アセット一覧（取得済み）

```
場所: D:\Clawdbot_Docker_20260125\data\workspace\apps\blender_assets\ambientcg\
取得済み: Concrete034（建物）/ Ground079S（道路）/ Metal027（金属）
```

**テクスチャファイル命名規則**:
```
{AssetID}_Color.png         ← Base Color
{AssetID}_NormalGL.png      ← Normal Map (OpenGL形式)
{AssetID}_Roughness.png     ← Roughness
{AssetID}_AmbientOcclusion.png  ← AO (オプション)
```

---

## 14. 次回再現手順（AIなしで実行可能）

```powershell
# 1. 環境確認
python -c "import yaml, psycopg2; print('OK')"

# 2. 別都市用config作成（templateをコピーして lat/lon を変更）
cp projects/CityCharacterPipeline/configs/template.yaml configs/myCity_dom.yaml
# → scene.name, character.fbx_path, position.lat/lon, render.output_dir を編集

# 3. 実行
cd projects/CityCharacterPipeline
python run_pipeline.py --config configs/myCity_dom.yaml

# 4. 品質確認 → 不合格なら改善ヒントに従い config 調整
# 5. 合格後 → --animate で動画生成
python run_pipeline.py --config configs/myCity_dom.yaml --animate
```
