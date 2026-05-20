"""material_enhancements.py

都市シーン・キャラクター向けBlender質感強化ライブラリ。

各 *_CODE 定数は generate_blender_script() からBlenderスクリプトへ注入される。
YAML city_enhancements セクションのパラメータで全機能を制御できるため、
渋谷以外の都市・ザク以外のキャラクターにも再利用可能。

機能:
  - 建物窓グリッド (手続き的ノード)
  - 道路白線オーバーレイ
  - 信号機ジオメトリ
  - キャラクター金属PBR

知識記録: record_enhancements() -> Turso DB + ByteRover Markdown
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT    = Path(__file__).resolve().parents[3]
BRV_DIR = ROOT / ".brv" / "context-tree" / "infrastructure" / "city_character_pipeline"

_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:change_me@127.0.0.1:5432/sim_trials",
)

# ─────────────────────────────────────────────────────────────────────────────
# デフォルトパラメータ（YAML city_enhancements で上書き可能）
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_PARAMS: dict = {
    "windows": {
        "enabled":        True,
        "floor_height_m": 3.5,   # 1フロア高さ(m)
        "win_width_m":    3.0,   # 窓1枚の幅(m)
        "mortar_ratio":   0.18,  # 壁フレーム幅の割合(0-1)
    },
    "road_markings": {
        "enabled":            True,
        "stripe_interval_m":  3.5,   # 白線の繰り返し間隔(m)
        "stripe_width_ratio": 0.10,  # 白線幅の割合(0-1)
    },
    "traffic_lights": {
        "enabled":   True,
        "count":     4,
        "positions": None,   # None -> 原点周辺を自動配置
    },
    "facade_details": {
        "enabled":      True,
        "max_buildings": 36,
        "max_distance": 95.0,
        "signs":        True,
        "roof_units":   True,
        "material_variation": True,
    },
    "character_metal": {
        "enabled":    True,
        "base_color": [0.10, 0.14, 0.06],  # MS-06F ダークオリーブグリーン
        "metallic":   0.80,
        "roughness":  0.45,
    },
}


def merge_params(yaml_enhancements: dict | None) -> dict:
    """YAMLのcity_enhancementsとデフォルトをマージして最終パラメータを返す。"""
    import copy
    result = copy.deepcopy(DEFAULT_PARAMS)
    if yaml_enhancements:
        for key, val in yaml_enhancements.items():
            if isinstance(val, dict) and key in result:
                result[key].update(val)
            else:
                result[key] = val
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Blenderスクリプトへ注入するコード（文字列定数）
# CFG / bpy はBlender実行コンテキストで利用可能
# ─────────────────────────────────────────────────────────────────────────────

WINDOW_OVERLAY_CODE = r'''
def _add_window_overlay(bldg_mat):
    """建物マテリアルに窓グリッドパターンをノードで追加する。

    X*Z modulo mask -> MixShader(concrete, dark_glass)
    パラメータ: CFG["city_enhancements"]["windows"]
    """
    if bldg_mat is None:
        return
    enh     = CFG.get("city_enhancements", {}).get("windows", {})
    if not enh.get("enabled", True):
        return
    floor_h = enh.get("floor_height_m", 3.5)
    win_w   = enh.get("win_width_m",    3.0)
    mortar  = enh.get("mortar_ratio",   0.18)
    try:
        nodes  = bldg_mat.node_tree.nodes
        links  = bldg_mat.node_tree.links
        bsdf   = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"),  None)
        if bsdf is None or output is None:
            return

        # -- テクスチャ座標 (Object = m単位ローカル座標) --
        tc   = nodes.new("ShaderNodeTexCoord")
        mapp = nodes.new("ShaderNodeMapping")
        mapp.inputs["Scale"].default_value = (1.0 / win_w, 1.0 / win_w, 1.0 / floor_h)
        links.new(tc.outputs["Object"], mapp.inputs["Vector"])

        sep = nodes.new("ShaderNodeSeparateXYZ")
        links.new(mapp.outputs["Vector"], sep.inputs["Vector"])

        # -- X方向マスク --
        mx = nodes.new("ShaderNodeMath"); mx.operation = "MODULO"
        mx.inputs[1].default_value = 1.0
        links.new(sep.outputs["X"], mx.inputs[0])
        gx = nodes.new("ShaderNodeMath"); gx.operation = "GREATER_THAN"
        gx.inputs[1].default_value = mortar
        links.new(mx.outputs["Value"], gx.inputs[0])

        # -- Z方向マスク --
        mz = nodes.new("ShaderNodeMath"); mz.operation = "MODULO"
        mz.inputs[1].default_value = 1.0
        links.new(sep.outputs["Z"], mz.inputs[0])
        gz = nodes.new("ShaderNodeMath"); gz.operation = "GREATER_THAN"
        gz.inputs[1].default_value = mortar
        links.new(mz.outputs["Value"], gz.inputs[0])

        # -- X * Z = 純粋な窓グリッドマスク --
        mul = nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        links.new(gx.outputs["Value"], mul.inputs[0])
        links.new(gz.outputs["Value"], mul.inputs[1])

        # -- ガラス窓BSDF (暗い反射ガラス) --
        win = nodes.new("ShaderNodeBsdfPrincipled")
        win.inputs["Base Color"].default_value = (0.04, 0.07, 0.14, 1.0)
        win.inputs["Roughness"].default_value  = 0.05
        try:
            win.inputs["Specular IOR Level"].default_value = 1.0
        except KeyError:
            pass

        # -- Mix: 壁(0)=コンクリート / 窓(1)=ガラス --
        mix = nodes.new("ShaderNodeMixShader")
        links.new(mul.outputs["Value"],  mix.inputs["Fac"])
        links.new(bsdf.outputs["BSDF"],  mix.inputs[1])
        links.new(win.outputs["BSDF"],   mix.inputs[2])
        links.new(mix.outputs["Shader"], output.inputs["Surface"])

        print("[Enhance] Window overlay -> " + bldg_mat.name
              + " floor=" + str(floor_h) + "m win=" + str(win_w) + "m", flush=True)
    except Exception as _we:
        print("[Enhance] Window overlay skip: " + str(_we), flush=True)
'''

ROAD_MARKINGS_CODE = r'''
def _add_road_markings():
    """道路白線を地面オーバーレイPlaneに手続き的パターンで追加する。

    X方向 modulo+threshold -> MixShader(transparent, white)
    パラメータ: CFG["city_enhancements"]["road_markings"]
    """
    enh         = CFG.get("city_enhancements", {}).get("road_markings", {})
    if not enh.get("enabled", True):
        return
    interval    = enh.get("stripe_interval_m",  3.5)
    width_ratio = enh.get("stripe_width_ratio",  0.10)
    margin      = CFG.get("terrain", {}).get("osm_bbox_margin_m", 200)
    try:
        bpy.ops.mesh.primitive_plane_add(size=margin * 1.6, location=(0, 0, 0.03))
        plane      = bpy.context.object
        plane.name = "Road_Markings"

        mat        = bpy.data.materials.new("Road_Line_Mat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        for n in list(nodes):
            nodes.remove(n)

        tc   = nodes.new("ShaderNodeTexCoord")
        mapp = nodes.new("ShaderNodeMapping")
        mapp.inputs["Scale"].default_value = (1.0 / interval, 1.0 / interval, 1.0)
        links.new(tc.outputs["Object"], mapp.inputs["Vector"])

        sep = nodes.new("ShaderNodeSeparateXYZ")
        links.new(mapp.outputs["Vector"], sep.inputs["Vector"])

        mx = nodes.new("ShaderNodeMath"); mx.operation = "MODULO"
        mx.inputs[1].default_value = 1.0
        links.new(sep.outputs["X"], mx.inputs[0])
        gx = nodes.new("ShaderNodeMath"); gx.operation = "GREATER_THAN"
        gx.inputs[1].default_value = 1.0 - width_ratio
        links.new(mx.outputs["Value"], gx.inputs[0])

        wb = nodes.new("ShaderNodeBsdfPrincipled")
        wb.inputs["Base Color"].default_value = (0.92, 0.92, 0.88, 1.0)
        wb.inputs["Roughness"].default_value  = 0.75

        tr  = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        links.new(gx.outputs["Value"], mix.inputs["Fac"])
        links.new(tr.outputs["BSDF"],  mix.inputs[1])
        links.new(wb.outputs["BSDF"],  mix.inputs[2])

        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(mix.outputs["Shader"], out.inputs["Surface"])
        plane.data.materials.append(mat)

        print("[Enhance] Road markings added interval=" + str(interval) + "m", flush=True)
    except Exception as _re:
        print("[Enhance] Road markings skip: " + str(_re), flush=True)
'''

TRAFFIC_LIGHTS_CODE = r'''
def _add_traffic_lights():
    """信号機(ポール+本体+赤灯Emission)を交差点付近に複数配置する。

    positions=None のとき原点周辺に等角度配置。
    パラメータ: CFG["city_enhancements"]["traffic_lights"]
    """
    enh       = CFG.get("city_enhancements", {}).get("traffic_lights", {})
    if not enh.get("enabled", True):
        return
    count     = enh.get("count", 4)
    positions = enh.get("positions", None)
    if positions is None:
        import math as _m
        _r = 18.0
        positions = [
            (_r * _m.cos(_m.radians(a + 45)), _r * _m.sin(_m.radians(a + 45)), 0)
            for a in range(0, 360, 360 // count)
        ][:count]
    try:
        # -- 共有マテリアル --
        pm = bpy.data.materials.new("TL_Pole_Mat")
        pm.use_nodes = True
        _pb = next(n for n in pm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        _pb.inputs["Base Color"].default_value = (0.12, 0.12, 0.12, 1.0)
        _pb.inputs["Metallic"].default_value   = 0.85
        _pb.inputs["Roughness"].default_value  = 0.35

        bm = bpy.data.materials.new("TL_Box_Mat")
        bm.use_nodes = True
        _bb = next(n for n in bm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        _bb.inputs["Base Color"].default_value = (0.06, 0.06, 0.06, 1.0)
        _bb.inputs["Roughness"].default_value  = 0.70

        rm = bpy.data.materials.new("TL_Red_Mat")
        rm.use_nodes = True
        for _n in list(rm.node_tree.nodes):
            rm.node_tree.nodes.remove(_n)
        _em = rm.node_tree.nodes.new("ShaderNodeEmission")
        _em.inputs["Color"].default_value    = (1.0, 0.05, 0.0, 1.0)
        _em.inputs["Strength"].default_value = 8.0
        _ou = rm.node_tree.nodes.new("ShaderNodeOutputMaterial")
        rm.node_tree.links.new(_em.outputs["Emission"], _ou.inputs["Surface"])

        for i, pos in enumerate(positions):
            lx, ly = float(pos[0]), float(pos[1])

            bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=5.5, location=(lx, ly, 2.75))
            pole = bpy.context.object
            pole.name = "TL_Pole_" + str(i)
            pole.data.materials.append(pm)

            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(lx, ly, 6.2))
            box = bpy.context.object
            box.scale = (0.5, 0.35, 1.2)
            bpy.ops.object.transform_apply(scale=True)
            box.name = "TL_Box_" + str(i)
            box.data.materials.append(bm)

            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(lx, ly - 0.18, 7.0))
            light = bpy.context.object
            light.name = "TL_Red_" + str(i)
            light.data.materials.append(rm)

        print("[Enhance] Traffic lights: " + str(len(positions)) + " placed", flush=True)
    except Exception as _te:
        print("[Enhance] Traffic lights skip: " + str(_te), flush=True)
'''

FACADE_DETAILS_CODE = r'''
def _add_facade_details():
    """Add lightweight facade details to nearby OSM buildings."""
    enh = CFG.get("city_enhancements", {}).get("facade_details", {})
    if not enh.get("enabled", True):
        return
    max_buildings = int(enh.get("max_buildings", 36))
    max_distance = float(enh.get("max_distance", 95.0))
    add_signs = bool(enh.get("signs", True))
    add_roof_units = bool(enh.get("roof_units", True))
    vary_material = bool(enh.get("material_variation", True))
    try:
        import math as _math
        camera_cfg = CFG.get("camera", {})
        cpos = camera_cfg.get("position", [0, -40, 6])
        cam_x, cam_y = float(cpos[0]), float(cpos[1])
        buildings = []
        for obj in bpy.data.objects:
            if obj.type != "MESH" or not obj.name.startswith("OSM_Building_"):
                continue
            pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
            if not pts:
                continue
            min_x = min(v.x for v in pts); max_x = max(v.x for v in pts)
            min_y = min(v.y for v in pts); max_y = max(v.y for v in pts)
            max_z = max(v.z for v in pts)
            cx = (min_x + max_x) * 0.5
            cy = (min_y + max_y) * 0.5
            dist = _math.hypot(cx - cam_x, cy - cam_y)
            if dist <= max_distance and max_z >= 5.0:
                buildings.append((dist, obj, min_x, max_x, min_y, max_y, max_z))
        buildings.sort(key=lambda item: item[0])

        sign_mats = []
        sign_colors = [
            (0.10, 0.45, 1.00, 1.0),
            (1.00, 0.18, 0.05, 1.0),
            (0.05, 0.90, 0.35, 1.0),
            (1.00, 0.72, 0.08, 1.0),
        ]
        for i, color in enumerate(sign_colors):
            mat = bpy.data.materials.new("Facade_Sign_Emission_" + str(i))
            mat.use_nodes = True
            for node in list(mat.node_tree.nodes):
                mat.node_tree.nodes.remove(node)
            em = mat.node_tree.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = color
            em.inputs["Strength"].default_value = 2.5
            out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
            mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
            sign_mats.append(mat)

        roof_mat = bpy.data.materials.new("Facade_Roof_Unit_Mat")
        roof_mat.use_nodes = True
        rb = next((n for n in roof_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if rb:
            rb.inputs["Base Color"].default_value = (0.18, 0.18, 0.17, 1.0)
            rb.inputs["Metallic"].default_value = 0.3
            rb.inputs["Roughness"].default_value = 0.55

        count = 0
        for idx, item in enumerate(buildings[:max_buildings]):
            _, obj, min_x, max_x, min_y, max_y, max_z = item
            width_x = max_x - min_x
            width_y = max_y - min_y
            cx = (min_x + max_x) * 0.5
            cy = (min_y + max_y) * 0.5

            if vary_material and obj.data.materials and obj.data.materials[0]:
                src = obj.data.materials[0]
                mat = src.copy()
                mat.name = "Facade_Var_" + obj.name
                if mat.use_nodes and mat.node_tree:
                    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                    if bsdf:
                        tint = 0.86 + ((idx % 7) * 0.035)
                        old = bsdf.inputs["Base Color"].default_value
                        bsdf.inputs["Base Color"].default_value = (
                            min(float(old[0]) * tint, 1.0),
                            min(float(old[1]) * tint, 1.0),
                            min(float(old[2]) * tint, 1.0),
                            1.0,
                        )
                obj.data.materials[0] = mat

            if add_signs and max_z > 8.0:
                face_y = min_y if abs(cam_y - min_y) < abs(cam_y - max_y) else max_y
                sign_w = max(2.5, min(width_x * 0.45, 8.0))
                sign_h = max(0.7, min(max_z * 0.08, 1.6))
                sign_z = min(max_z * 0.38, 7.5)
                y_offset = -0.06 if face_y == min_y else 0.06
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, face_y + y_offset, sign_z))
                sign = bpy.context.object
                sign.name = "Facade_Sign_" + str(idx)
                sign.scale = (sign_w * 0.5, 0.035, sign_h * 0.5)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                sign.data.materials.append(sign_mats[idx % len(sign_mats)])

            if add_roof_units and max(width_x, width_y) > 7.0:
                unit_w = min(max(width_x * 0.18, 1.2), 3.5)
                unit_d = min(max(width_y * 0.18, 1.2), 3.5)
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, max_z + 0.35))
                unit = bpy.context.object
                unit.name = "Facade_RoofUnit_" + str(idx)
                unit.scale = (unit_w * 0.5, unit_d * 0.5, 0.35)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                unit.data.materials.append(roof_mat)

            count += 1
        print("[Enhance] Facade details: " + str(count) + " buildings", flush=True)
    except Exception as _fe:
        print("[Enhance] Facade details skip: " + str(_fe), flush=True)
'''

CHARACTER_METAL_CODE = r'''
def _apply_metal_pbr(char_obj):
    """キャラクター全子Meshに金属PBRマテリアルを適用する。

    base_color / metallic / roughness は YAML city_enhancements.character_metal で設定。
    例: MS-06F Zaku II -> base_color=[0.10,0.14,0.06] metallic=0.80
    """
    if char_obj is None:
        return
    enh = CFG.get("city_enhancements", {}).get("character_metal", {})
    if not enh.get("enabled", True):
        return
    bc  = enh.get("base_color", [0.10, 0.14, 0.06])
    met = float(enh.get("metallic",  0.80))
    rou = float(enh.get("roughness", 0.45))
    try:
        meshes = [c for c in char_obj.children_recursive if c.type == "MESH"]
        if not meshes:
            return
        mat = bpy.data.materials.new("Char_Metal_PBR")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (float(bc[0]), float(bc[1]), float(bc[2]), 1.0)
        bsdf.inputs["Metallic"].default_value   = met
        bsdf.inputs["Roughness"].default_value  = rou
        for mesh in meshes:
            if mesh.data.materials:
                mesh.data.materials[0] = mat
            else:
                mesh.data.materials.append(mat)
        print("[Enhance] Metal PBR: " + str(len(meshes)) + " meshes"
              + " metal=" + str(met) + " rough=" + str(rou), flush=True)
    except Exception as _me:
        print("[Enhance] Metal PBR skip: " + str(_me), flush=True)
'''


def get_injection_code(params: dict) -> str:
    """全強化コードをBlenderスクリプトへ注入する文字列として返す。"""
    return (
        "# --- CityEnhancement Library (auto-injected) ---\n"
        + WINDOW_OVERLAY_CODE
        + ROAD_MARKINGS_CODE
        + TRAFFIC_LIGHTS_CODE
        + FACADE_DETAILS_CODE
        + CHARACTER_METAL_CODE
        + "# --- CityEnhancement Library end ---\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 知識記録（DB + ByteRover）
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_table(conn) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS city_enhancements_log (
            id          SERIAL PRIMARY KEY,
            scene_name  TEXT,
            params_json JSONB,
            applied_at  TIMESTAMPTZ DEFAULT now()
        )
    """)
    conn.commit()
    cur.close()


def record_enhancements(
    scene_name: str,
    yaml_enhancements: dict,
    db_url: str | None = None,
) -> None:
    """適用した強化パラメータをDB(city_enhancements_log)とBytRover Markdownに記録する。

    Args:
        scene_name:        YAMLのscene.name
        yaml_enhancements: YAMLのcity_enhancementsセクション全体
        db_url:            PostgreSQL接続URL (省略時は環境変数DATABASE_URL)
    """
    params   = merge_params(yaml_enhancements)
    url      = db_url or _DB_URL
    now_str  = datetime.now().strftime("%Y%m%d_%H%M%S")

    # -- DB記録 --
    try:
        import psycopg2
        conn = psycopg2.connect(url, client_encoding="utf8")
        _ensure_table(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO city_enhancements_log (scene_name, params_json) VALUES (%s, %s)",
            (scene_name, json.dumps(params, ensure_ascii=False)),
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"[Enhance] DB recorded: city_enhancements_log scene={scene_name}", flush=True)
    except Exception as e:
        print(f"[Enhance] DB record skip: {e}", flush=True)

    # -- ByteRover Markdown --
    try:
        BRV_DIR.mkdir(parents=True, exist_ok=True)
        md_path = BRV_DIR / f"enhancements_{scene_name}_{now_str}.md"

        win  = params.get("windows", {})
        road = params.get("road_markings", {})
        tl   = params.get("traffic_lights", {})
        cm   = params.get("character_metal", {})

        lines = [
            f"# CityEnhancement Log: {scene_name}",
            f"applied_at: {now_str}",
            "",
            "## windows",
            f"  enabled:        {win.get('enabled')}",
            f"  floor_height_m: {win.get('floor_height_m')}",
            f"  win_width_m:    {win.get('win_width_m')}",
            f"  mortar_ratio:   {win.get('mortar_ratio')}",
            "",
            "## road_markings",
            f"  enabled:            {road.get('enabled')}",
            f"  stripe_interval_m:  {road.get('stripe_interval_m')}",
            f"  stripe_width_ratio: {road.get('stripe_width_ratio')}",
            "",
            "## traffic_lights",
            f"  enabled: {tl.get('enabled')}",
            f"  count:   {tl.get('count')}",
            "",
            "## character_metal",
            f"  enabled:    {cm.get('enabled')}",
            f"  base_color: {cm.get('base_color')}",
            f"  metallic:   {cm.get('metallic')}",
            f"  roughness:  {cm.get('roughness')}",
            "",
            "## reuse_guide",
            "  - 別都市: terrain.osm_bbox_margin_m + character.fbx_path だけ変更",
            "  - 別キャラ: character_metal.base_color を機体色に合わせて変更",
            "  - 窓サイズ: windows.floor_height_m / win_width_m でビル種別に対応",
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[Enhance] ByteRover recorded: {md_path.name}", flush=True)
    except Exception as e:
        print(f"[Enhance] ByteRover skip: {e}", flush=True)
