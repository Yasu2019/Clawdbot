"""terrain_builder.py — OSM/PLATEAU両対応地形データ取得モジュール

Blender外部（run_pipeline.py）から呼ばれ、OSM建物データをJSONで保存する。
Blender内部では scene_builder.py の _build_osm_terrain() がそのJSONを読んでメッシュ生成する。

data_source:
    "osm"        → Overpass API から建物取得 → osm_data.json に保存
    "plateau"    → 既存 blend_source を使用（このモジュールは何もしない）
    "blend_only" → 地形なし（キャラクターのみ）
"""
from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 30  # seconds
CACHE_TTL_SEC = 86400  # 24時間キャッシュ


# ══════════════════════════════════════════════════════════════
# 公開API
# ══════════════════════════════════════════════════════════════

def prepare_terrain(config: dict, output_dir: Path) -> dict:
    """data_source に応じて地形データを準備し、追加情報をconfigに注入して返す。

    Returns:
        config（osm_json_path などが追加された状態）
    """
    terrain_cfg = config.get("terrain", {})
    data_source = terrain_cfg.get("data_source", "blend_only")

    if data_source == "osm":
        char_cfg = config.get("character", {})
        pos_cfg  = char_cfg.get("position", {})
        lat = pos_cfg.get("lat", 35.6580)
        lon = pos_cfg.get("lon", 139.7016)
        margin_m = terrain_cfg.get("osm_bbox_margin_m", 500)

        osm_path = _get_osm_data(lat, lon, margin_m, output_dir)
        config.setdefault("terrain", {})["osm_json_path"] = str(osm_path)
        config["terrain"]["osm_center_lat"] = lat
        config["terrain"]["osm_center_lon"] = lon
        print(f"[TerrainBuilder] OSM data ready: {osm_path.name} "
              f"({_count_buildings(osm_path)} buildings)", flush=True)

    elif data_source == "plateau":
        print(f"[TerrainBuilder] PLATEAU mode: using blend_source", flush=True)

    else:
        print(f"[TerrainBuilder] blend_only mode: no terrain generation", flush=True)

    return config


# ══════════════════════════════════════════════════════════════
# OSMデータ取得
# ══════════════════════════════════════════════════════════════

def _get_osm_data(lat: float, lon: float, margin_m: float, output_dir: Path) -> Path:
    """Overpass APIから建物データを取得してJSONに保存する。キャッシュあり。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / f"osm_data_{lat:.4f}_{lon:.4f}_{int(margin_m)}.json"

    # キャッシュ確認
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL_SEC:
            print(f"[TerrainBuilder] Using cached OSM data ({age/3600:.1f}h old)", flush=True)
            return cache_path

    # bbox計算
    south, west, north, east = _compute_bbox(lat, lon, margin_m)
    print(f"[TerrainBuilder] Querying Overpass API: bbox=({south:.4f},{west:.4f},{north:.4f},{east:.4f})", flush=True)

    # Overpassクエリ（建物 + 道路 + 公園）
    query = f"""
[out:json][timeout:{OVERPASS_TIMEOUT}];
(
  way["building"]({south},{west},{north},{east});
  way["highway"]["highway"~"^(primary|secondary|tertiary|residential|pedestrian)$"]({south},{west},{north},{east});
  way["landuse"~"^(park|grass|recreation_ground)$"]({south},{west},{north},{east});
);
out geom;
""".strip()

    try:
        data = _overpass_query(query)
        # 中心点・スケール情報を付加
        data["_meta"] = {
            "center_lat": lat,
            "center_lon": lon,
            "margin_m": margin_m,
            "bbox": [south, west, north, east],
            "fetched_at": time.time(),
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"[TerrainBuilder] Saved: {cache_path.name}", flush=True)
        return cache_path

    except Exception as e:
        print(f"[TerrainBuilder] Overpass API failed: {e}", flush=True)
        # フォールバック: 空のOSMデータを作成して処理続行
        fallback = {
            "elements": [],
            "_meta": {"center_lat": lat, "center_lon": lon, "margin_m": margin_m,
                      "bbox": [south, west, north, east], "fetched_at": time.time(),
                      "error": str(e)},
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(fallback, f)
        return cache_path


def _overpass_query(query: str) -> dict:
    """Overpass APIにPOSTクエリを送信してJSONを返す。"""
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "CityCharacterPipeline/1.0 (clawstack)"},
    )
    with urllib.request.urlopen(req, timeout=OVERPASS_TIMEOUT + 5) as resp:
        return json.loads(resp.read())


def _compute_bbox(lat: float, lon: float, margin_m: float) -> tuple:
    """中心緯度経度と余白(m)からbboxを計算する。"""
    dlat = margin_m / 111319.0
    dlon = margin_m / (111319.0 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def _count_buildings(path: Path) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return sum(1 for e in d.get("elements", [])
                   if e.get("tags", {}).get("building"))
    except Exception:
        return 0


# ══════════════════════════════════════════════════════════════
# Blenderスクリプト用コードスニペット生成
# ══════════════════════════════════════════════════════════════

OSM_BLENDER_CODE = '''
# ── OSM地形生成（Blender内部で実行） ──────────────────────────
def _latlon_to_xy(lat, lon, lat0, lon0):
    """緯度経度をBlender XY座標(m)に変換する。"""
    dx = (lon - lon0) * math.cos(math.radians(lat0)) * 111319.0
    dy = (lat - lat0) * 111319.0
    return dx, dy


def _build_osm_terrain():
    """OSM JSONからBlenderメッシュを生成する。"""
    import bmesh
    osm_path = CFG.get("terrain", {}).get("osm_json_path", "")
    if not osm_path or not os.path.isfile(osm_path):
        print("[TerrainBuilder] OSM JSON not found, skipping terrain", flush=True)
        return

    with open(osm_path, encoding="utf-8") as f:
        osm = json.load(f)

    meta = osm.get("_meta", {})
    lat0 = meta.get("center_lat", 35.6580)
    lon0 = meta.get("center_lon", 139.7016)
    margin = meta.get("margin_m", 500)
    elements = osm.get("elements", [])

    mat_cfg = CFG.get("materials", {})
    roughness = mat_cfg.get("roughness_override", 0.7)

    # 地面プレーン（グレー平面）
    bpy.ops.mesh.primitive_plane_add(size=margin * 2, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "OSM_Ground"
    gmat = _get_or_make_mat("OSM_Ground_Mat")
    gmat.use_nodes = True
    bsdf = next((n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = gmat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.25, 0.25, 0.25, 1.0)
    bsdf.inputs["Roughness"].default_value  = 0.9
    ground.data.materials.append(gmat)

    # マテリアル準備
    bldg_mat = _pbr_from_ambientcg(mat_cfg.get("building_texture", "Concrete034"), roughness)
    road_mat = _pbr_from_ambientcg(mat_cfg.get("road_texture", "Ground079S"), roughness + 0.1)

    bldg_count = 0
    road_count  = 0

    for elem in elements:
        if elem.get("type") != "way":
            continue
        geometry = elem.get("geometry", [])
        if len(geometry) < 3:
            continue

        tags = elem.get("tags", {})
        is_building = bool(tags.get("building"))
        is_road     = bool(tags.get("highway"))
        is_park     = bool(tags.get("landuse") in ("park", "grass", "recreation_ground"))

        # XY変換
        verts_2d = []
        for pt in geometry:
            x, y = _latlon_to_xy(pt["lat"], pt["lon"], lat0, lon0)
            verts_2d.append((x, y))

        # 閉じたポリゴン（最初と最後が同一点）の場合、最後を除く
        if len(verts_2d) > 1 and verts_2d[0] == verts_2d[-1]:
            verts_2d = verts_2d[:-1]

        if len(verts_2d) < 3:
            continue

        if is_building:
            # 建物高さ推定
            try:
                height = float(tags.get("height", 0))
            except (ValueError, TypeError):
                height = 0.0
            if height <= 0:
                try:
                    levels = int(tags.get("building:levels", 3))
                except (ValueError, TypeError):
                    levels = 3
                height = levels * 3.5

            # bmeshで押し出し
            bm = bmesh.new()
            verts = [bm.verts.new((x, y, 0.0)) for x, y in verts_2d]
            try:
                face = bm.faces.new(verts)
                bmesh.ops.extrude_face_region(bm, geom=[face])
                # 押し出した上面の頂点をZ=heightに移動
                for v in bm.verts:
                    if v.co.z > 0.01:
                        v.co.z = height
                bm.normal_update()
                mesh = bpy.data.meshes.new(f"OSM_Building_{bldg_count}")
                bm.to_mesh(mesh)
                bm.free()
                obj = bpy.data.objects.new(f"OSM_Building_{bldg_count}", mesh)
                bpy.context.collection.objects.link(obj)
                if bldg_mat:
                    obj.data.materials.append(bldg_mat)
                bldg_count += 1
            except Exception:
                bm.free()

        elif is_road:
            # 道路: 薄いプレーンとして追加（Z=0.01で地面より少し上）
            bm = bmesh.new()
            verts = [bm.verts.new((x, y, 0.01)) for x, y in verts_2d]
            if len(verts) >= 2:
                for i in range(len(verts) - 1):
                    bm.edges.new((verts[i], verts[i+1]))
            mesh = bpy.data.meshes.new(f"OSM_Road_{road_count}")
            bm.to_mesh(mesh)
            bm.free()
            obj = bpy.data.objects.new(f"OSM_Road_{road_count}", mesh)
            bpy.context.collection.objects.link(obj)
            if road_mat:
                obj.data.materials.append(road_mat)
            road_count += 1

        elif is_park:
            bm = bmesh.new()
            verts = [bm.verts.new((x, y, 0.02)) for x, y in verts_2d]
            try:
                bm.faces.new(verts)
                bm.normal_update()
                mesh = bpy.data.meshes.new(f"OSM_Park_{bldg_count}")
                bm.to_mesh(mesh)
                bm.free()
                obj = bpy.data.objects.new(f"OSM_Park_{bldg_count}", mesh)
                bpy.context.collection.objects.link(obj)
                park_mat = _get_or_make_mat("Park_Mat")
                park_mat.use_nodes = True
                bsdf = next((n for n in park_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf:
                    bsdf.inputs["Base Color"].default_value = (0.15, 0.45, 0.15, 1.0)
                    bsdf.inputs["Roughness"].default_value  = 0.95
                obj.data.materials.append(park_mat)
            except Exception:
                bm.free()

    print(f"[TerrainBuilder] OSM mesh: {bldg_count} buildings, {road_count} roads", flush=True)
'''


def get_osm_blender_code() -> str:
    """Blenderスクリプトに埋め込むOSM地形生成コードを返す。"""
    return OSM_BLENDER_CODE
