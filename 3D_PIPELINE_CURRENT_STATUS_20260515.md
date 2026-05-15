# 3D Pipeline Current Status - Atsugi Terrain Grounding

Date: 2026-05-15 JST
Prepared for: VS Code restart / continuation handover

## 1. Current Goal

厚木3Dマップ上に、地形・建物・メカモデルを同じBlenderシーン内で表示し、メカを地形上に立たせる。

今回の主眼は、WebGLビューアの巨大データ読み込み問題をいったん避け、Blenderのオフライン処理で正しい接地状態を作ること。

## 2. Latest Result

最終的に、地形・建物・Zakuが同じ診断レンダー内に表示され、Zakuは地形メッシュ上に立つ状態まで到達した。

### Generated Outputs

- Script:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\place_mecha_on_atsugi_terrain.py`
- Output blend:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded.blend`
- Output diagnostic image:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Diagnostic.png`
- Output report:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\atsugi_terrain_grounding_report.json`

### Visual Status

The latest diagnostic image shows:

- Green Zaku visible.
- Terrain surface visible.
- Building blocks visible on/near terrain in the same scene.
- Zaku standing on terrain.
- The view is an orthographic diagnostic view, not a cinematic final shot.

## 3. Important Files and Inputs

### Base Blender Scene

- `D:\Clawdbot_Docker_20260125\Gundam\Atsugi_Front_Final.blend`

This scene contains the building meshes. It does not include the terrain DEM mesh.

### Terrain OBJ

- `D:\Clawdbot_Docker_20260125\apps\agi_designer\viewer\exports\Atsugi_Terrain.obj`

Observed size:

- About 112 MB
- About 3,070,983 vertices
- About 1,023,661 polygons

### Map FBX

- `D:\Clawdbot_Docker_20260125\apps\agi_designer\viewer\exports\Atsugi_Map.fbx`
- `D:\Clawdbot_Docker_20260125\Gundam\Atsugi_Front_Final.fbx`

Observed size:

- About 184 MB

### Existing Older Script

- `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\place_mecha_on_atsugi_map.py`

This script uses a simple city minimum Z plane. It is not sufficient for terrain-aware placement.

## 4. What Failed Before Success

### Failure 1: Single Z Plane

The older placement logic used:

```python
ground_z = city_min.z
```

This treats the whole city as a flat plane. It fails for real terrain and causes buildings or mecha to appear floating or disconnected from the true ground.

### Failure 2: Bounding Box Scaling Terrain to City

The first attempt in `place_mecha_on_atsugi_terrain.py` imported `Atsugi_Terrain.obj` and scaled the terrain bounding box into the building bounding box.

That was wrong.

Symptoms:

- Zaku was visible.
- Buildings appeared far above or disconnected.
- Terrain was not aligned with the visible city.
- The image looked broken.

Reason:

- The Web viewer does not scale the terrain to the city bounding box.
- The terrain DEM and FBX map have different exported coordinate origins, but simple bbox scaling distorts the terrain.

### Failure 3: Raycast at City Center

Blender `ray_cast` at the city center initially failed because the city center was not directly over a terrain face after naive alignment.

Fallback to nearest XY terrain vertex revealed important facts:

- With bbox scaling, nearest terrain vertex distance at city center was about `244` units.
- With Web-style no-scale alignment before horizontal patch snapping, nearest distance was over `3000` units.
- This means the building FBX and DEM cannot be trusted with a naive origin/bbox transform.

### Failure 4: Building Batch Z Correction

Moving all buildings to terrain height was tested conceptually and disabled.

Reason:

- Building-to-terrain XY correspondence is not fully reliable yet.
- If each `Bldg` is force-moved by nearest/raycast terrain height, buildings can jump or float unnaturally.
- Therefore `ADJUST_BUILDINGS = False` is intentional.

## 5. Final Working Approach

The final successful approach follows the Web viewer more closely.

### Axis Mapping

The OBJ terrain raw coordinates are transformed into Blender working coordinates as:

- raw OBJ `X` -> Blender `X`
- raw OBJ `Z` -> Blender `Y`
- raw OBJ `Y` -> Blender `Z`

This is needed because Blender OBJ import rotates the terrain around X, and the raw OBJ stores horizontal axes differently from the desired scene.

### No Bounding Box Scale

The final approach does **not** scale the terrain to the building bounding box.

Current method:

```text
method = web_viewer_center_no_scale
scale = [1.0, 1.0, 1.0]
```

### Horizontal Patch Snap

The terrain is first center-aligned like the Web viewer. Then the nearest real terrain patch is horizontally snapped toward the city center.

Current report values:

```json
"terrain_horizontal_snap_enabled": true,
"terrain_horizontal_offset": [-3312.98053, -19.917969]
```

This step was necessary because, after pure center alignment, the terrain face near city center was still too far away.

### Vertical Offset

The script finds a useful terrain height around the city center and offsets terrain vertically relative to an anchor building street level.

Current report value:

```json
"terrain_vertical_offset": -28.540001
```

### Anchor Building

The script selects the first building with significant vertical height as the anchor.

Current anchor:

```json
"anchor_building": {
  "name": "Bldg",
  "center": [66.274208, 701.102905, 9.605],
  "street_z": 0.0,
  "height": 19.209999
}
```

### Zaku Placement

Zaku is placed near the anchor building and then snapped to the nearest real terrain vertex/face if needed.

Current report:

```json
"mecha": {
  "name": "Zaku_Armature",
  "scale_factor": 9.0,
  "terrain_z": -14.339844,
  "hit_xy_distance": 0.0,
  "snap_to_nearest_terrain_vertex": true,
  "placement_xy": [495.128357, 721.553284]
}
```

`hit_xy_distance = 0.0` is good. It means the final Zaku placement is directly on a usable terrain sample/raycast position.

## 6. Current Script Behavior

Script:

```text
projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py
```

Main behavior:

1. Opens:
   - `Gundam\Atsugi_Front_Final.blend`
2. Finds building meshes:
   - names starting with `Bldg`
3. Imports:
   - `apps\agi_designer\viewer\exports\Atsugi_Terrain.obj`
4. Applies raw OBJ axis conversion:
   - raw X -> scene X
   - raw Z -> scene Y
   - raw Y -> scene Z
5. Uses Web-viewer style no-scale center alignment.
6. Horizontally snaps a real terrain patch toward city center.
7. Applies vertical terrain offset using anchor building street level.
8. Builds:
   - KDTree terrain sampler
   - BVH terrain raycast structure
9. Leaves buildings unmoved:
   - `ADJUST_BUILDINGS = False`
10. Places Zaku on terrain:
   - `SNAP_MECHA_TO_NEAREST_TERRAIN_VERTEX = True`
11. Saves:
   - `.blend`
   - `.png`
   - `.json`

## 7. Important Constants

In `place_mecha_on_atsugi_terrain.py`:

```python
MECHA_NAME = "Zaku_Armature"
TARGET_HEIGHT_M = 18.0
UPRIGHT_ROTATION_DEGREES = (90.0, 0.0, 0.0)
ADJUST_BUILDINGS = False
SNAP_MECHA_TO_NEAREST_TERRAIN_VERTEX = True
ALIGN_TERRAIN_LIKE_WEB_VIEWER = True
SNAP_TERRAIN_PATCH_TO_CITY_CENTER = True
```

Do not casually change `ADJUST_BUILDINGS` to `True` yet.

## 8. Why Buildings Are Not Yet Correctly Grounded

Buildings are visible together with terrain and Zaku, but building grounding is not considered solved.

Reason:

- The PLATEAU building FBX appears to have lost or normalized its original EPSG/world coordinate origin.
- The DEM terrain OBJ still reflects a large real coordinate range.
- Web viewer comments confirm this:
  - Map FBX was centered/lost true EPSG coordinates.
  - Terrain still has true-ish DEM coordinates.
  - The viewer shifts terrain center and then raycasts near center.

Therefore, building-by-building terrain correction needs a more reliable matching rule before activation.

## 9. What To Do Next

Recommended continuation order:

1. Keep current successful diagnostic as baseline.
2. Improve camera/render only if needed.
3. Derive a better terrain-to-building XY transform.
4. Do not batch-move buildings until the transform is proven.
5. Add a diagnostic overlay or markers:
   - city center
   - anchor building
   - Zaku placement
   - terrain patch snap source/target
6. Test several candidate anchor buildings, not just `Bldg`.
7. Once terrain/building XY relation is reliable, enable a controlled building subset correction:
   - start with 5 buildings
   - save report
   - render
   - visually inspect
8. Only after that, consider all 394 buildings.

## 10. Suggested Next Implementation

Create a new diagnostic mode in the same script:

```python
ANCHOR_BUILDING_NAME = "Bldg"
BUILDING_TEST_LIMIT = 5
ADJUST_BUILDINGS = "subset"
```

The subset mode should:

- choose 5 buildings around the anchor
- compute terrain hit distance
- only move a building if raycast hit distance is near zero
- skip if nearest terrain distance is too large
- write skipped/moved details into JSON
- render a close and wide diagnostic image

Acceptance criteria:

- No buildings jump into the sky.
- Zaku remains on terrain.
- Terrain and buildings remain visible in one image.
- JSON clearly says which objects were moved or skipped.

## 11. Commands To Re-run

Run the current successful pipeline:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\place_mecha_on_atsugi_terrain.py"
```

Open the diagnostic image:

```powershell
Start-Process "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Diagnostic.png"
```

Open the output blend:

```powershell
Start-Process "D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded.blend"
```

## 12. Known Caveats

- The current diagnostic image is not a final beauty render.
- Zaku is visually standing on terrain, but this is a diagnostic placement.
- Building grounding is intentionally not activated.
- Terrain mesh is very large and low-level faceted; WebGL should still use glTF/Draco or simplification later.
- Browser viewer may still fail if loading original 184 MB FBX + 112 MB OBJ directly.
- The current method is safer than bbox scaling, but still a heuristic.

## 13. ByteRover Notes

Relevant decisions were queued into ByteRover:

- Bbox scaling terrain into city was a failed approach.
- Web viewer style no-scale center alignment plus patch snap produced the current success.
- Building batch correction is unsafe until XY transform is validated.

If ByteRover search hits token limits, use this file as the primary restart handover.

## 14. Git / Working Tree Notes

New or changed paths from this work:

- `projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py`
- `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/`
- `3D_PIPELINE_CURRENT_STATUS_20260515.md`

No Docker compose files were modified.
No Rails protected paths were modified.
No destructive file operations were performed.

## 15. 2026-05-16 Update: Cleaner Terrain / Building Display

The terrain-to-building display was improved after the initial 5-building subset test.

Current successful diagnostic:

- Script:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\place_mecha_on_atsugi_terrain.py`
- Output images:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Subset_Close.png`
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Subset_Wide.png`
- Output report:
  - `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\atsugi_terrain_grounding_subset_report.json`

Key changes:

- Horizontal terrain snap mode changed to `best_building_overlap`.
- The script now scores candidate terrain offsets against building center coverage instead of snapping only to city center.
- Best offset found:
  - `[-3912.98053, -619.917969]`
- Building overlap score:
  - `near_building_count = 394`
  - `mean_nearest_distance = 1.60439`
  - `max_nearest_distance = 2.932804`
- All 394 buildings passed the direct terrain raycast guard and were adjusted.
- Close and wide diagnostic cameras were adjusted for cleaner visual confirmation.

Visual result:

- The main building cluster now appears on the terrain surface.
- Terrain relief, roads/ditches, and surrounding building groups are visible in the same render.
- The previous large horizontal separation between the main building cluster and terrain is no longer visible in the wide diagnostic render.

Still not final beauty render:

- This is a Blender Workbench diagnostic render.
- Terrain mesh is still raw/faceted.
- The method is still heuristic and should be preserved as a diagnostic baseline before any WebGL/export simplification work.

## 16. 2026-05-16 Update: Building Floating Correction

User visual review correctly found that some buildings still appeared to float above the terrain. The earlier center-point grounding was not sufficient on sloped terrain.

Current correction:

- Each building footprint is sampled on a 5 x 5 terrain grid.
- Initial dark foundation pads reduced some gaps but looked like raised pedestals in the diagnostic view.
- Current setting uses the lowest sampled terrain point minus `BUILDING_EMBED_DEPTH = 0.75`.
- Dark foundations are disabled.
- Thin terrain-colored contact pads are generated under adjusted building footprints:
  - `BUILDING_CONTACT_PAD_ENABLED = True`
  - `BUILDING_CONTACT_PAD_MARGIN = 0.45`
- All 394 buildings were adjusted in the regenerated diagnostic report.

Latest verified outputs:

- `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Subset_Close.png`
- `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\Atsugi_Terrain_Grounded_Subset_Wide.png`
- `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\atsugi_terrain_grounding\atsugi_terrain_grounding_subset_report.json`

Validation:

- `python -m py_compile projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py`
- Blender 5.1 background render completed successfully.
- Manual visual check was performed on both close and wide PNGs after regeneration.

Notes:

- The contact pads are intentional diagnostic terrain caps to prevent visible air gaps around box buildings on raw/faceted terrain.
- The previous Telegram images sent before this correction should be treated as outdated.
