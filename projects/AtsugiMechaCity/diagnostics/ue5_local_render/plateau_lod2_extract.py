"""
plateau_lod2_extract.py

PLATEAU CityGML LOD2 建物データを 100m 半径で切り出し、
Blender インポート用 JSON に変換する。

出力: plateau_lod2_radius100.json
  {
    "station": {"lat": ..., "lon": ...},
    "radius_m": 100.0,
    "buildings": [
      {
        "id": "bldg_xxx",
        "faces": [
          {
            "polygon_id": "face_xxx",
            "vertices": [[x,y,z], ...],   # Blender座標系 (メートル)
            "texture_path": "...jpg",      # None if no texture
            "uvs": [[u,v], ...]            # Blender UV (v反転済み), vertices と同数
          },
          ...
        ]
      },
      ...
    ]
  }
"""

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer

# -----------------------------------------------------------------------
# 設定
# -----------------------------------------------------------------------
ROOT = Path(r"D:\Clawdbot_Docker_20260125")
PLATEAU_BLDG = ROOT / "data" / "PLATEAU" / "Atsugi" / "udx" / "bldg"
OUT_JSON = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "ue5_local_render" / "plateau_lod2_radius100.json"

HON_ATSUGI_LAT = 35.4393389
HON_ATSUGI_LON = 139.3643379
RADIUS_M = 200.0
MARGIN_M = 20.0   # 境界バッファ（建物がまたがる場合の余裕）

# カメラ位置（sealed camera: road_origin + (-18m, -64m)）付近の建物を除外
# road_origin ≈ station中心なので station-relative (-18, -64)

# FBX export axis_forward="-Y" により UE5_y = -Blender_y * 100
# sealed camera: UE5(-1800, -6400) → Blender(-18, +64)
CAMERA_EXCLUDE_CENTER = (-18.0, 64.0)   # Blender座標系 (m)
CAMERA_EXCLUDE_RADIUS = 80.0            # 除外半径 (m)
CAMERA_Z = 23.7                          # カメラ高度 海抜m相当

# LOD2 データありタイル（確認済み）
LOD2_TILES = [
    "53390297_bldg_6697_op.gml",
    "53391206_bldg_6697_op.gml",
    "53391207_bldg_6697_op.gml",
    "53391218_bldg_6697_op.gml",
    "53391228_bldg_6697_op.gml",
    "53391229_bldg_6697_op.gml",
    "53391238_bldg_6697_op.gml",
    "53391239_bldg_6697_op.gml",
    "53391248_bldg_6697_op.gml",
]

# XML 名前空間
NS_GML  = "http://www.opengis.net/gml"
NS_BLDG = "http://www.opengis.net/citygml/building/2.0"
NS_APP  = "http://www.opengis.net/citygml/appearance/2.0"
NS_CORE = "http://www.opengis.net/citygml/2.0"

TAG_BLDG    = f"{{{NS_BLDG}}}Building"
TAG_POLYGON = f"{{{NS_GML}}}Polygon"
TAG_POSLIST = f"{{{NS_GML}}}posList"
TAG_RING    = f"{{{NS_GML}}}LinearRing"
TAG_APP     = f"{{{NS_APP}}}ParameterizedTexture"
TAG_URI     = f"{{{NS_APP}}}imageURI"
TAG_TARGET  = f"{{{NS_APP}}}target"
TAG_UVLIST  = f"{{{NS_APP}}}textureCoordinates"
TAG_BLDG_PART = f"{{{NS_BLDG}}}BuildingPart"

# -----------------------------------------------------------------------
# 座標変換: EPSG:6697 (JGD2011 地理座標) → Blender空間 (メートル)
# -----------------------------------------------------------------------
transformer = Transformer.from_crs("EPSG:6697", "EPSG:6677", always_xy=False)
_sy, _sx, _ = transformer.transform(HON_ATSUGI_LAT, HON_ATSUGI_LON, 0.0)
STATION = (float(_sx), float(-_sy))

def geo_to_blender(lats, lons, alts):
    """lat/lon/alt リスト → Blender XYZ (meter, station 相対)"""
    ys, xs, zs = transformer.transform(lats, lons, alts)
    return [(float(x - STATION[0]), float(-y - STATION[1]), float(z))
            for x, y, z in zip(xs, ys, zs)]

def parse_poslist(text):
    """gml:posList テキスト → (lats, lons, alts) リスト"""
    vals = text.strip().split()
    lats, lons, alts = [], [], []
    for i in range(0, len(vals) - 2, 3):
        lats.append(float(vals[i]))
        lons.append(float(vals[i + 1]))
        alts.append(float(vals[i + 2]))
    return lats, lons, alts

def within_radius(pts, r):
    for x, y, _z in pts:
        if math.hypot(x, y) <= r:
            return True
    return False

def near_camera(pts):
    """建物がカメラ除外ゾーンに掛かる場合 True を返す。
    ①半径チェック: 任意頂点がEXCLUDE_RADIUS内 → 除外
    ②バウンディングボックスにカメラが含まれる → 除外（内部インシデント防止）
    """
    cx, cy = CAMERA_EXCLUDE_CENTER
    for x, y, _z in pts:
        if math.hypot(x - cx, y - cy) <= CAMERA_EXCLUDE_RADIUS:
            return True
    # BB containment check
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    if (min(xs) <= cx <= max(xs) and
            min(ys) <= cy <= max(ys) and
            min(zs) <= CAMERA_Z <= max(zs)):
        return True
    return False

# -----------------------------------------------------------------------
# Step 1: Appearance データ収集 (polygon_id → {texture_path, uvs_per_ring})
# -----------------------------------------------------------------------
def collect_appearances(gml_path):
    """
    {polygon_id: {"texture": str, "ring_uvs": {ring_id: [[u,v],...]}}}
    """
    appearances = {}
    tree = ET.parse(gml_path)
    root = tree.getroot()
    tile_dir = gml_path.parent
    for ptex in root.iter(TAG_APP):
        uri_el = ptex.find(TAG_URI)
        if uri_el is None or not uri_el.text:
            continue
        texture_path = str(tile_dir / uri_el.text.strip())

        for target in ptex.findall(TAG_TARGET):
            poly_ref = target.get("uri", "").lstrip("#")
            if not poly_ref:
                continue
            ring_uvs = {}
            for tc in target.iter(TAG_UVLIST):
                ring_ref = tc.get("ring", "").lstrip("#")
                if tc.text:
                    vals = list(map(float, tc.text.strip().split()))
                    uvs = []
                    for j in range(0, len(vals) - 1, 2):
                        u = vals[j]
                        v = 1.0 - vals[j + 1]   # CityGML→Blender: V反転
                        uvs.append([u, v])
                    ring_uvs[ring_ref] = uvs
            appearances[poly_ref] = {"texture": texture_path, "ring_uvs": ring_uvs}
    return appearances

# -----------------------------------------------------------------------
# Step 2: LOD2 建物ジオメトリ収集
# -----------------------------------------------------------------------
def parse_polygon(poly_el, appearances):
    """
    gml:Polygon 要素 → face dict
    """
    poly_id = poly_el.get(f"{{{NS_GML}}}id", "")
    ring_el = poly_el.find(f".//{TAG_RING}")
    poslist_el = poly_el.find(f".//{TAG_POSLIST}")
    if poslist_el is None or not poslist_el.text:
        return None

    ring_id = ring_el.get(f"{{{NS_GML}}}id", "") if ring_el is not None else ""
    lats, lons, alts = parse_poslist(poslist_el.text)
    if len(lats) < 3:
        return None
    # 最後の頂点が最初と同じ場合は除外（閉じたリング）
    verts = geo_to_blender(lats, lons, alts)
    if len(verts) > 1 and verts[-1] == verts[0]:
        verts = verts[:-1]
    if len(verts) < 3:
        return None
    # 地面スラブ除外: 全頂点のz最大値が1m以下の面はスキップ
    if max(v[2] for v in verts) < 1.0:
        return None

    tex_path = None
    uvs = [[0.0, 0.0]] * len(verts)
    app = appearances.get(poly_id)
    if app:
        tex_path = app["texture"]
        ring_uvs = app["ring_uvs"].get(ring_id, [])
        if len(ring_uvs) >= len(verts):
            uvs = ring_uvs[:len(verts)]
        elif ring_uvs:
            # UV数が合わない場合は最初の値で埋める
            uvs = ring_uvs[:len(verts)] + [ring_uvs[-1]] * (len(verts) - len(ring_uvs))

    return {
        "polygon_id": poly_id,
        "vertices": verts,
        "texture_path": tex_path,
        "uvs": uvs,
    }

def collect_buildings(gml_path, appearances, radius):
    buildings = []
    tree = ET.parse(gml_path)
    root = tree.getroot()

    for bldg in root.iter(TAG_BLDG):
        bldg_id = bldg.get(f"{{{NS_GML}}}id", "unknown")
        faces = []
        for poly in bldg.findall(f".//{TAG_POLYGON}"):
            face = parse_polygon(poly, appearances)
            if face:
                faces.append(face)

        if not faces:
            continue
        # 半径フィルタ: いずれかの面の頂点が範囲内
        all_verts = [v for f in faces for v in f["vertices"]]
        if not within_radius(all_verts, radius + MARGIN_M):
            continue
        # カメラ除外ゾーン内の建物はスキップ（カメラ内部インシデント防止）
        if near_camera(all_verts):
            continue

        buildings.append({"id": bldg_id, "faces": faces})

    return buildings

# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main():
    print(f"Station: {STATION[0]:.2f}, {STATION[1]:.2f} (Blender origin)")
    print(f"Radius: {RADIUS_M}m (+{MARGIN_M}m margin)")

    all_buildings = []
    for tile_name in LOD2_TILES:
        gml_path = PLATEAU_BLDG / tile_name
        if not gml_path.exists():
            print(f"  SKIP (not found): {tile_name}")
            continue
        print(f"  Parsing {tile_name} ...")
        apps = collect_appearances(gml_path)
        bldgs = collect_buildings(gml_path, apps, RADIUS_M)
        print(f"    appearances: {len(apps)}, buildings in radius: {len(bldgs)}")
        all_buildings.extend(bldgs)

    # ID 重複排除（複数タイルにまたがる場合）
    seen = set()
    unique_buildings = []
    for b in all_buildings:
        if b["id"] not in seen:
            seen.add(b["id"])
            unique_buildings.append(b)

    result = {
        "station": {"lat": HON_ATSUGI_LAT, "lon": HON_ATSUGI_LON},
        "radius_m": RADIUS_M,
        "building_count": len(unique_buildings),
        "buildings": unique_buildings,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    face_total = sum(len(b["faces"]) for b in unique_buildings)
    tex_set = {f["texture_path"] for b in unique_buildings for f in b["faces"] if f["texture_path"]}
    print(f"\nDone: {len(unique_buildings)} buildings, {face_total} faces, {len(tex_set)} textures")
    print(f"Output: {OUT_JSON}")

if __name__ == "__main__":
    main()
