"""CityCharacterPipeline — Blenderシーンビルダー

YAMLコンフィグからBlender Pythonスクリプトを生成する。
マテリアル強化・HDRI/太陽照明・接地AO・アニメーション対応。
Blender内で実行されるスクリプトを文字列として返す。
"""
from __future__ import annotations
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

# ── Blenderスクリプトテンプレート ────────────────────────────────
_BLENDER_SCRIPT = '''
import bpy, math, os, glob, json, random
from pathlib import Path
from mathutils import Vector, Euler

CFG      = json.loads("__CFG__")
OUT_DIR  = Path(CFG["render"]["output_dir"])
OUT_DIR.mkdir(parents=True, exist_ok=True)
PREFIX   = CFG["render"]["output_prefix"]
AMCG_DIR = Path(CFG["materials"]["ambientcg_dir"])

# アニメーション接地グローバル（_apply_mixamo_action_walk → _render_animation で共有）
_WALK_ACTIVE      = False
_WALK_ARM_NAME    = ""
_WALK_CONST_Z     = 0.0
_WALK_ORIG_X      = 0.0
_WALK_ORIG_Y      = 0.0
_WALK_DIR         = [0.0, -1.0, 0.0]
_WALK_STEP_M      = 5.0
_WALK_TOTAL_F     = 90
_WALK_FRAME_START = 1


# ── 機体別公式全高テーブル（Gundam公式スペック） ────────────────
_MECHA_HEIGHT_M = {
    "dom":       18.6, "ms09":  18.6,
    "zaku":      17.5, "ms06":  17.5,
    "gm":        18.0, "rgm79": 18.0,
    "gelgoog":   19.2, "ms14":  19.2,
    "gouf":      18.7, "ms07":  18.7,
    "gogg":      17.5, "msm03": 17.5,
    "zgok":      18.4, "msm07": 18.4,
    "guncannon": 17.9, "rx77":  17.9,
    "guntank":   15.6, "rx75":  15.6,
    "gundam":    18.0, "rx78":  18.0,
    "rickdias":  20.0, "rms099":20.0,
}

def _lookup_height_m(name_hint: str, default: float = 18.0) -> float:
    """モデル名から公式全高を返す。未知の場合はdefaultを使用。"""
    nl = name_hint.lower()
    for key, h in _MECHA_HEIGHT_M.items():
        if key in nl:
            return h
    return default


# ── mixamo_action_preview.py 由来のBBox計算（depsgraph評価済み） ──
def _bounds_for_objects(objects, use_depsgraph=True):
    """全オブジェクトのワールド座標BBoxを返す (min_v, max_v)。"""
    import mathutils
    depsgraph = bpy.context.evaluated_depsgraph_get() if use_depsgraph else None
    min_v = mathutils.Vector((1e9, 1e9, 1e9))
    max_v = mathutils.Vector((-1e9, -1e9, -1e9))
    found = False
    for obj in objects:
        try:
            src = obj.evaluated_get(depsgraph) if depsgraph else obj
            for corner in src.bound_box:
                world = src.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    if world[i] < min_v[i]: min_v[i] = world[i]
                    if world[i] > max_v[i]: max_v[i] = world[i]
            found = True
        except Exception:
            pass
    if not found:
        loc = objects[0].matrix_world.translation if objects else mathutils.Vector()
        return loc.copy(), loc.copy()
    return min_v, max_v


def _get_char_meshes(char_obj):
    """キャラクターArmatureの子Meshオブジェクト一覧を返す。"""
    meshes = [o for o in char_obj.children_recursive if o.type == "MESH"]
    if not meshes:
        # 子がない場合はシーン内の全Meshを対象に（旧Codex blend対応）
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"
                  and o.parent == char_obj]
    return meshes


# ── ユーティリティ ──────────────────────────────────────────────
def _get_or_make_mat(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)

def _make_dark_asphalt_mat():
    """OSM道路用：手続き的ダークアスファルトマテリアル（砂色Ground079S回避）。"""
    mat = bpy.data.materials.get("OSM_Dark_Asphalt")
    if mat:
        return mat
    mat = bpy.data.materials.new("OSM_Dark_Asphalt")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    # Diffuse BSDF (Lambertian): Fresnel無し → grazing角度でも暗く見える
    bsdf = nodes.new("ShaderNodeBsdfDiffuse")
    out  = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Color"].default_value  = (0.05, 0.05, 0.05, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    return mat

def _pbr_from_ambientcg(asset_id: str, roughness_override: float = 0.7):
    """ambientCGアセットからPrincipled BSDFマテリアルを生成する。"""
    asset_dir = AMCG_DIR / asset_id
    if not asset_dir.exists():
        return None
    def _find(suffix):
        for ext in ("png", "jpg"):
            p = asset_dir / f"{asset_id}_{suffix}.{ext}"
            if p.exists(): return str(p)
        # 代替パターン
        for f in asset_dir.glob(f"*{suffix}*"):
            if f.suffix.lower() in (".png",".jpg"): return str(f)
        return None

    color_path  = _find("Color")
    normal_path = _find("NormalGL") or _find("Normal")
    rough_path  = _find("Roughness")
    ao_path     = _find("AmbientOcclusion")

    if not color_path:
        return None

    mat = _get_or_make_mat(f"PBR_{asset_id}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    out  = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Object座標 + Mapping: UVマップなしのOSMメッシュでも物理スケールでタイリング
    # OSM建物はワールド原点に配置されるため Object座標 = ワールド座標(m単位)
    # scale=0.2 → 5mごとに1タイル繰り返し（コンクリート壁に適切）
    tc   = nodes.new("ShaderNodeTexCoord")
    mapp = nodes.new("ShaderNodeMapping")
    mapp.inputs["Scale"].default_value = (0.2, 0.2, 0.2)
    links.new(tc.outputs["Object"], mapp.inputs["Vector"])

    def _tex(path, colorspace="sRGB"):
        t = nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        t.image.colorspace_settings.name = colorspace
        links.new(mapp.outputs["Vector"], t.inputs["Vector"])
        return t

    # Color
    ct = _tex(color_path)
    links.new(ct.outputs["Color"], bsdf.inputs["Base Color"])

    # Roughness
    if rough_path:
        rt = _tex(rough_path, "Non-Color")
        links.new(rt.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = roughness_override

    # Normal
    if normal_path:
        nt = _tex(normal_path, "Non-Color")
        nm = nodes.new("ShaderNodeNormalMap")
        links.new(nt.outputs["Color"], nm.inputs["Color"])
        links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

    print(f"[SceneBuilder] PBR mat created: {asset_id}", flush=True)
    return mat


def _procedural_sky():
    """手続き型空（Blender組み込み）でワールド照明を設定する。"""
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    sky = nodes.new("ShaderNodeTexSky")
    # Blender 5.1: NISHITA -> MULTIPLE_SCATTERING に名称変更
    for _sky_type in ("NISHITA", "MULTIPLE_SCATTERING", "HOSEK_WILKIE"):
        try:
            sky.sky_type = _sky_type
            break
        except TypeError:
            continue
    # 太陽角度（設定値から）
    sun_cfg = CFG["lighting"].get("sun", {})
    sun_elev_deg = _sun_elevation(
        sun_cfg.get("lat", 35.44),
        sun_cfg.get("lon", 139.41),
        sun_cfg.get("hour", 14),
    )
    sky.sun_elevation = math.radians(max(5, sun_elev_deg))
    sky.sun_rotation  = math.radians(180)  # 南向き

    bg  = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = CFG["lighting"].get("hdri_strength", 1.0)
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(sky.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    print(f"[SceneBuilder] Procedural sky set (elevation={sun_elev_deg:.1f}deg)", flush=True)


def _sun_elevation(lat_deg, lon_deg, hour_local):
    """緯度・経度・時刻から太陽仰角(度)を近似計算する。"""
    lat = math.radians(lat_deg)
    day_of_year = 135  # 5月15日 ≒ 135日
    decl = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81))))
    hour_angle = math.radians(15 * (hour_local - 12))
    sin_alt = (math.sin(lat) * math.sin(decl) +
               math.cos(lat) * math.cos(decl) * math.cos(hour_angle))
    return math.degrees(math.asin(max(-1, min(1, sin_alt))))


def _hdri_world(hdri_path: str):
    """Poly Haven HDRIファイルをワールド照明に適用する。"""
    if not hdri_path or not os.path.isfile(hdri_path):
        _procedural_sky()
        return
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    env = nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(hdri_path, check_existing=True)
    bg  = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = CFG["lighting"].get("hdri_strength", 1.2)
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(env.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    print(f"[SceneBuilder] HDRI: {os.path.basename(hdri_path)}", flush=True)


def _setup_sun():
    sun_cfg = CFG["lighting"].get("sun", {})
    if not sun_cfg.get("enabled", True):
        return
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
    sun = bpy.context.object
    sun.name = "Sun_Physical"
    sun.data.energy = sun_cfg.get("energy", 5.0)
    sun.data.angle  = math.radians(0.5)  # 太陽の見かけの大きさ
    elev = _sun_elevation(
        sun_cfg.get("lat", 35.44),
        sun_cfg.get("lon", 139.41),
        sun_cfg.get("hour", 14),
    )
    sun.rotation_euler = Euler((math.radians(90 - elev), 0, math.radians(180)), "XYZ")
    print(f"[SceneBuilder] Sun: energy={sun.data.energy}, elev={elev:.1f}deg", flush=True)


def _setup_fill_lights():
    for i, fl in enumerate(CFG["lighting"].get("fill_lights", [])):
        bpy.ops.object.light_add(type=fl.get("type","AREA"), location=fl["position"])
        light = bpy.context.object
        light.name = f"FillLight_{i}"
        light.data.energy = fl.get("energy", 200)
        if fl.get("type","AREA") == "AREA":
            light.data.size = 8.0
        col = fl.get("color", [1,1,1])
        light.data.color = col
    print(f"[SceneBuilder] Fill lights: {len(CFG['lighting'].get('fill_lights', []))}", flush=True)


def _add_sky_ambient():
    """巨大面光源で空からの環境光を再現 — 都市峡谷の暗転防止。"""
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 300))
    sky = bpy.context.object
    sky.name = "SkyAmbient"
    sky.data.energy = 0.05    # 明るすぎる地面色の主因のため大幅削減
    sky.data.size   = 800
    sky.data.color  = (0.55, 0.72, 1.0)
    sky.rotation_euler = Euler((math.radians(180), 0, 0), "XYZ")
    print("[SceneBuilder] Sky ambient: AREA 800m 5000W @ z=300", flush=True)


def _enhance_materials():
    """既存マテリアルをPBRに強化する。建物・道路・金属を識別して適用。"""
    mat_cfg  = CFG["materials"]
    roughness = mat_cfg.get("roughness_override", 0.7)

    # 既存マテリアルを再利用（nodes.clear()で窓オーバーレイが消えるのを防ぐ）
    _bldg_name = "PBR_" + mat_cfg.get("building_texture","Concrete034")
    _road_name = "PBR_" + mat_cfg.get("road_texture","Ground079S")
    _mtl_name  = "PBR_" + mat_cfg.get("metal_texture","Metal027")
    bldg_mat  = bpy.data.materials.get(_bldg_name) or _pbr_from_ambientcg(mat_cfg.get("building_texture","Concrete034"), roughness)
    road_mat  = bpy.data.materials.get(_road_name) or _pbr_from_ambientcg(mat_cfg.get("road_texture","Ground079S"), roughness + 0.1)
    metal_mat = bpy.data.materials.get(_mtl_name)  or _pbr_from_ambientcg(mat_cfg.get("metal_texture","Metal027"), roughness - 0.2)

    if not mat_cfg.get("apply_to_existing", True):
        return

    # キャラクター子Meshの集合（これらにはPBR建物テクスチャを適用しない）
    char_mesh_ids = set()
    for scene_obj in bpy.context.scene.objects:
        if scene_obj.type == "ARMATURE":
            for child in scene_obj.children_recursive:
                char_mesh_ids.add(child.name)

    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        name_l = obj.name.lower()
        # キャラクター子Mesh・AO系・地面・道路オーバーレイ・信号機はスキップ
        if obj.name in char_mesh_ids:
            continue
        if any(k in name_l for k in ("contact_ao","shadow","preview_ground","osm_ground",
                                      "road_markings","road_line","tl_")):
            continue
        # マテリアル分類
        if any(k in name_l for k in ("bldg","building","wall","house","tower")):
            target = bldg_mat
        elif any(k in name_l for k in ("osm_road","tran","street","walk","crosswalk","park")):
            target = _make_dark_asphalt_mat()  # Ground079S(砂色)を使わず手続きアスファルト
        elif any(k in name_l for k in ("metal","steel","pipe","rail","corrugated")):
            target = metal_mat
        else:
            target = bldg_mat  # デフォルト: コンクリート

        if target is None:
            _ensure_principled(obj, roughness)
            continue
        # Blender 5.1: material_slots[0].link='OBJECT' で確実に反映
        if obj.material_slots:
            obj.material_slots[0].link = 'OBJECT'
            obj.material_slots[0].material = target
        elif obj.data.materials:
            obj.data.materials[0] = target
        else:
            obj.data.materials.append(target)

    print("[SceneBuilder] Material enhancement done", flush=True)


def _ensure_principled(obj, roughness):
    """Emission系マテリアルをPrincipled BSDFに変換して基本的な質感を付与。"""
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None:
            continue
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = 0.0
            continue
        # Emissionのみの場合: 置き換え
        emit = next((n for n in nodes if n.type == "EMISSION"), None)
        if emit:
            color = emit.inputs["Color"].default_value[:]
            out   = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
            new_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            new_bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
            new_bsdf.inputs["Roughness"].default_value  = roughness
            if out:
                mat.node_tree.links.new(new_bsdf.outputs["BSDF"], out.inputs["Surface"])


def _get_char_bbox(char_obj):
    """Armatureの子Meshを depsgraph 評価済みで統合BBoxを返す。
    mixamo_action_preview.py の bounds_for_objects パターンを踏襲。
    """
    import mathutils
    meshes = _get_char_meshes(char_obj)
    if meshes:
        min_v, max_v = _bounds_for_objects(meshes, use_depsgraph=True)
        span = max_v.z - min_v.z
        if span > 0.1:
            # BBoxをリスト形式で返す（旧インターフェース互換）
            return [min_v, max_v,
                    mathutils.Vector((min_v.x, min_v.y, min_v.z)),
                    mathutils.Vector((max_v.x, max_v.y, max_v.z))]
    # フォールバック: Armatureのworldロケーション + 公式全高
    loc = char_obj.matrix_world.translation
    name_hint = char_obj.name
    height_m = _lookup_height_m(name_hint,
                                CFG.get("character",{}).get("height_m", 18.0))
    cx, cy, cz = loc.x, loc.y, loc.z
    print(f"[SceneBuilder] BBox fallback (no mesh children): loc=({cx:.1f},{cy:.1f},{cz:.1f}), h={height_m}m", flush=True)
    return [
        mathutils.Vector((cx - 5, cy - 5, cz)),
        mathutils.Vector((cx + 5, cy + 5, cz + height_m)),
        mathutils.Vector((cx - 5, cy - 5, cz)),
        mathutils.Vector((cx + 5, cy + 5, cz + height_m)),
    ]


def _setup_contact_ao(char_obj=None):
    """キャラクター足元にAOシャドウ用プレーンを配置する。"""
    ao_cfg = CFG.get("contact_ao", {})
    if not ao_cfg.get("enabled", True):
        return

    if char_obj is None:
        print("[SceneBuilder] ContactAO: no character object, skipping", flush=True)
        return

    # Armature＋子Meshを含むBBox
    bb = _get_char_bbox(char_obj)
    foot_z  = min(v.z for v in bb) + 0.05
    cx = sum(v.x for v in bb) / len(bb)
    cy = sum(v.y for v in bb) / len(bb)

    radius  = ao_cfg.get("radius", 3.0)
    strength = ao_cfg.get("strength", 0.6)

    # AO Shadow Catcherプレーン
    bpy.ops.mesh.primitive_circle_add(radius=radius, vertices=32, location=(cx, cy, foot_z))
    ao_plane = bpy.context.object
    ao_plane.name = "ContactAO_ShadowCatcher"

    if ao_cfg.get("shadow_catcher", True):
        ao_plane.is_shadow_catcher = True

    # 暗化マテリアル（透明度付きAO効果）
    mat = _get_or_make_mat("ContactAO_Mat")
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value   = (0.0, 0.0, 0.0, 1.0)
    bsdf.inputs["Roughness"].default_value    = 1.0
    bsdf.inputs["Alpha"].default_value        = strength * 0.5
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    ao_plane.data.materials.append(mat)

    # 足元スポットライト（接地影の強調）
    bpy.ops.object.light_add(type="SPOT", location=(cx, cy, foot_z + 2.0))
    spot = bpy.context.object
    spot.name = "ContactAO_Spot"
    spot.data.energy    = 50.0
    spot.data.spot_size = math.radians(60)
    spot.data.shadow_soft_size = 0.5
    spot.rotation_euler = Euler((math.radians(180), 0, 0), "XYZ")

    print(f"[SceneBuilder] ContactAO placed at ({cx:.2f},{cy:.2f},{foot_z:.2f}) r={radius}", flush=True)


def _setup_dof(char_obj=None):
    """被写界深度（DoF）— キャラクターフォーカス、f/2.8 シネマ感。"""
    cam = bpy.context.scene.camera
    if cam is None or char_obj is None:
        print("[SceneBuilder] DoF: no camera/character, skip", flush=True)
        return
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = char_obj
    cam.data.dof.aperture_fstop = 5.6
    print(f"[SceneBuilder] DoF enabled: focus={char_obj.name}, f/5.6", flush=True)


def _setup_volumetric_atmosphere():
    """Volume Scatter は暗転の主因になるため無効化（密度0で実質スキップ）。"""
    print("[SceneBuilder] Volumetric atmosphere: disabled (prevents darkening)", flush=True)


def _setup_color_management():
    """カラーマネジメント — Filmic で暗部を保持しつつ自然な階調。"""
    scene = bpy.context.scene
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "None"  # High Contrast は暗部を潰す
    except Exception:
        try:
            scene.view_settings.view_transform = "Filmic"
            scene.view_settings.look = "None"
        except Exception:
            pass
    _exposure = CFG.get("render", {}).get("exposure", -1.0)
    scene.view_settings.exposure = _exposure
    scene.view_settings.gamma = 1.0
    print(f"[SceneBuilder] Color management: AgX/Filmic + exposure={_exposure}EV", flush=True)


def _setup_compositor_effects():
    """コンポジター後処理: Glare + ColorBalance + LensDist。
    Blender 5.1でAPIが変更されたため全体をtry/exceptで保護する。
    """
    try:
        scene = bpy.context.scene
        scene.use_nodes = True
        bpy.context.view_layer.update()

        # Blender 5.1: scene.node_tree が廃止された場合のフォールバック
        node_tree = None
        for _attr in ("node_tree", "compositing_nodetree", "compositor_node_tree"):
            node_tree = getattr(scene, _attr, None)
            if node_tree is not None:
                break

        if node_tree is None:
            print("[SceneBuilder] Compositor: node_tree not available in this Blender version, skipping", flush=True)
            return

        nodes = node_tree.nodes
        links = node_tree.links

        # 既存ノードをクリアして再構築
        for n in list(nodes):
            if n.type not in ("R_LAYERS", "COMPOSITE"):
                nodes.remove(n)

        rl   = next((n for n in nodes if n.type == "R_LAYERS"), None)
        comp = next((n for n in nodes if n.type == "COMPOSITE"), None)
        if rl is None:
            rl = nodes.new("CompositorNodeRLayers")
        if comp is None:
            comp = nodes.new("CompositorNodeComposite")

        # Glare — 太陽・ハイライ��のブルーム
        glare = nodes.new("CompositorNodeGlare")
        glare.glare_type = "STREAKS"
        glare.threshold  = 0.85
        glare.streaks    = 4
        glare.quality    = "LOW"
        glare.mix        = 0.0
        glare.size       = 7

        # Color Balance — 映画的色調整
        colbal = nodes.new("CompositorNodeColorBalance")
        colbal.correction_method = "ASC_CDL"
        colbal.slope  = (1.05, 1.00, 0.94)
        colbal.offset = (0.00, 0.00, 0.01)
        colbal.power  = (1.00, 1.00, 1.00)

        # Lens Distortion — わずかなバレル歪みで実���感
        lens = nodes.new("CompositorNodeLensDist")
        lens.use_fit = True
        lens.inputs["Distortion"].default_value = -0.015
        lens.inputs["Dispersion"].default_value = 0.003

        # チェーン: RenderLayers → Glare → ColorBalance → LensDist → Composite
        links.new(rl.outputs["Image"],     glare.inputs["Image"])
        links.new(glare.outputs["Image"],  colbal.inputs["Image"])
        links.new(colbal.outputs["Image"], lens.inputs["Image"])
        links.new(lens.outputs["Image"],   comp.inputs["Image"])
        print("[SceneBuilder] Compositor: Glare + ColorBalance + LensDist", flush=True)
    except Exception as _e:
        print(f"[SceneBuilder] Compositor effects skipped: {_e}", flush=True)


def _setup_camera(char_obj=None):
    """カメラを設定する。char_obj が渡された場合はそこから自動計算する。"""
    cam_cfg = CFG["camera"]
    lens = cam_cfg.get("lens_mm", 85)
    res  = cam_cfg.get("resolution", [1920, 1080])
    import mathutils

    if char_obj is not None:
        # depsgraph評価済みBBoxで正確なサイズを取得（mixamo_action_preview.py方式）
        bpy.context.view_layer.update()
        meshes = _get_char_meshes(char_obj)
        if meshes:
            min_v, max_v = _bounds_for_objects(meshes, use_depsgraph=True)
            height = max_v.z - min_v.z
            cx = (min_v.x + max_v.x) * 0.5
            cy = (min_v.y + max_v.y) * 0.5
            foot_z = min_v.z
            print(f"[SceneBuilder] BBox DEBUG: min_z={min_v.z:.2f} max_z={max_v.z:.2f} height={height:.2f}m cx={cx:.2f} cy={cy:.2f}", flush=True)
        else:
            loc = char_obj.matrix_world.translation
            cx, cy, foot_z = loc.x, loc.y, loc.z
            height = 0.0
        # 公式全高テーブルでフォールバック
        if height < 1.0:
            height = _lookup_height_m(char_obj.name,
                                      CFG.get("character",{}).get("height_m", 18.0))
        # YAMLにposition明示設定があればYAML優先（auto-framingをスキップ）
        yaml_pos = cam_cfg.get("position")
        yaml_tgt = cam_cfg.get("target")
        if yaml_pos and any(abs(v) > 0.01 for v in yaml_pos):
            pos = tuple(yaml_pos)
            tgt = tuple(yaml_tgt) if yaml_tgt else (cx, cy, foot_z + height * 0.5)
            print(f"[SceneBuilder] Camera YAML pos used: {pos}", flush=True)
        else:
            dist  = height * 3.5
            cam_z = foot_z + height * 1.3
            pos = (cx, cy - dist, cam_z)
            tgt = (cx, cy, foot_z + height * 0.5)
            print(f"[SceneBuilder] Camera auto-framed: char=({cx:.1f},{cy:.1f},{foot_z:.1f}), h={height:.1f}m, dist={dist:.1f}m", flush=True)
    else:
        pos = cam_cfg.get("position", [0, -30, 5])
        tgt = cam_cfg.get("target",   [0,  0,  9])

    # 既存の Pipeline カメラを再利用または新規作成
    cam_obj = bpy.data.objects.get("Camera_Pipeline")
    if cam_obj is None:
        bpy.ops.object.camera_add(location=pos)
        cam_obj = bpy.context.object
        cam_obj.name = "Camera_Pipeline"
    else:
        cam_obj.location = pos

    bpy.context.scene.camera = cam_obj
    direction = (mathutils.Vector(tgt) - mathutils.Vector(pos)).normalized()
    cam_obj.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()
    cam_obj.data.lens = lens
    cam_obj.data.sensor_fit = "AUTO"
    cam_obj.data.sensor_width = 36.0
    cam_obj.data.clip_start = 0.01
    # clip_end を距離の3倍 or 最低2000m に設定（巨大キャラ対応）
    _cam_dist = mathutils.Vector(pos).length if char_obj is None else (mathutils.Vector(pos) - mathutils.Vector(tgt)).length
    cam_obj.data.clip_end = max(_cam_dist * 3.0, 2000.0)

    scene = bpy.context.scene
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    # FOVデバッグ情報
    import math as _math
    _rx, _ry = res[0], res[1]
    _sw = 36.0
    _hfov = 2 * _math.degrees(_math.atan(_sw / 2 / lens))
    _vfov = 2 * _math.degrees(_math.atan(_sw / 2 / lens * _ry / _rx))
    print(f"[SceneBuilder] Camera FOV debug: h={_hfov:.1f}° v={_vfov:.1f}° half_v={_vfov/2:.1f}°", flush=True)
    print(f"[SceneBuilder] Camera: pos=({pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}), lens={lens}mm, clip_end={cam_obj.data.clip_end:.0f}m", flush=True)


def _setup_render():
    ren_cfg = CFG["render"]
    scene   = bpy.context.scene
    scene.render.engine = ren_cfg.get("engine","CYCLES")
    scene.cycles.device = ren_cfg.get("device","CPU")
    # デフォルト128spp+OIDN（64から倍増・写実品質）
    scene.cycles.samples = ren_cfg.get("samples", 128)
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = ren_cfg.get("denoiser","OPENIMAGEDENOISE")
    scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    # 16bit PNG（HDRダイナミックレンジ保持）
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    # 解像度: render.resolution → camera.resolution → デフォルトの順で参照
    _cam_res = CFG.get("camera", {}).get("resolution", [2048, 1152])
    res = ren_cfg.get("resolution", _cam_res)
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    print(f"[SceneBuilder] Render: {scene.render.engine} {scene.cycles.samples}spp {res[0]}x{res[1]}", flush=True)


def _setup_animation():
    anim_cfg = CFG.get("animation", {})
    if not anim_cfg.get("enabled", False):
        return
    scene = bpy.context.scene
    scene.frame_start = anim_cfg.get("frame_start", 1)
    scene.frame_end   = anim_cfg.get("total_frames", 120)
    scene.render.fps  = anim_cfg.get("fps", 24)

    cam_motion = anim_cfg.get("camera_motion", {})
    if cam_motion.get("type") == "orbit":
        cam = bpy.context.scene.camera
        if cam is None:
            return
        r = cam_motion.get("orbit_radius", 30.0)
        z = cam_motion.get("orbit_z", 6.0)
        # キャラクター実座標からorbit中心とターゲットを計算
        import mathutils as _mua
        cx, cy = 0.0, 0.0
        tgt_z = CFG.get("character",{}).get("height_m", 18.0) * 0.55
        if char_obj is not None:
            try:
                _meshes_a = _get_char_meshes(char_obj)
                if _meshes_a:
                    _mn, _mx = _bounds_for_objects(_meshes_a, use_depsgraph=True)
                    cx = (_mn.x + _mx.x) * 0.5
                    cy = (_mn.y + _mx.y) * 0.5
                    tgt_z = _mn.z + (_mx.z - _mn.z) * 0.55
                    r = max(r, (_mx.z - _mn.z) * 3.5)
                    z  = _mn.z + (_mx.z - _mn.z) * 0.35
                else:
                    loc = char_obj.matrix_world.translation
                    cx, cy = loc.x, loc.y
            except Exception:
                pass
        total = scene.frame_end - scene.frame_start + 1
        for f in range(scene.frame_start, scene.frame_end + 1):
            angle = 2 * math.pi * (f - scene.frame_start) / total
            cam.location = (cx + r * math.sin(angle), cy - r * math.cos(angle), z)
            cam.keyframe_insert("location", frame=f)
            tgt = _mua.Vector((cx, cy, tgt_z))
            direction = (tgt - _mua.Vector(cam.location)).normalized()
            cam.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()
            cam.keyframe_insert("rotation_euler", frame=f)
    # キャラクターモーション
    char_motion = anim_cfg.get("character_motion", {})
    if char_motion.get("type") == "mixamo_action":
        _apply_mixamo_action_walk(scene)
    elif char_motion.get("type") == "tpose_march":
        _apply_tpose_march(scene)
    print(f"[SceneBuilder] Animation: {scene.frame_end}frames, cam={cam_motion.get('type')}", flush=True)


def _apply_tpose_march(scene):
    """T-pose前進マーチ + プログラム的脚スイング。
    ザク固有プロポーション対応: Mixamoアクション不使用でZ浮き/屈み問題を回避。
    大腿骨を左右交互に±amp_deg スイング、膝を振り出し時に曲げる。"""
    import math
    anim_cfg = CFG.get("animation", {})
    char_cfg = anim_cfg.get("character_motion", {})
    step_m   = float(char_cfg.get("step_length_m", 12.0))
    walk_dir = char_cfg.get("walk_direction", [0.0, -1.0, 0.0])

    char_name = CFG.get("character", {}).get("name", "")
    arm = bpy.data.objects.get(char_name) or next(
        (o for o in bpy.data.objects if o.type == "ARMATURE"), None
    )
    if arm is None:
        print("[WalkAnim] アーマチャーが見つかりません", flush=True)
        return False

    total_f     = scene.frame_end - scene.frame_start + 1
    orig_loc    = arm.location.copy()
    step_period = 20    # frames per step cycle (30fps → 1.5歩/秒)
    bounce_amp  = 0.35  # m
    thigh_amp   = math.radians(20)   # 大腿骨スイング幅 (±20°)
    knee_amp    = math.radians(15)   # 膝曲げ最大 (15°)

    # Mixamoボーン名 (mixamorig: プレフィックスあり)
    # (bone_name, phase, is_knee, amp_override)
    # 脚スイング + 腕スイング（逆位相で自然な歩行感）
    swing_bones = [
        ("mixamorig:LeftUpLeg",  0.0,     False, thigh_amp),      # 左大腿: 前振り=位相0
        ("mixamorig:RightUpLeg", math.pi, False, thigh_amp),      # 右大腿: 逆位相
        ("mixamorig:LeftLeg",    0.0,     True,  knee_amp),       # 左膝: 前振り時に曲げ
        ("mixamorig:RightLeg",   math.pi, True,  knee_amp),       # 右膝
        ("mixamorig:LeftArm",    math.pi, False, math.radians(10)),  # 左腕: 右脚と逆位相
        ("mixamorig:RightArm",   0.0,     False, math.radians(10)),  # 右腕
    ]
    found_bones = [(n, p, k, a) for n, p, k, a in swing_bones if arm.pose.bones.get(n)]
    print(f"[WalkAnim] スイングボーン検出: {[n for n,_,_,_ in found_bones]}", flush=True)

    print(f"[WalkAnim] T-poseマーチ+レッグスイング開始 ({total_f}f, step={step_period}f)...", flush=True)
    for fi in range(total_f):
        frame    = scene.frame_start + fi
        progress = fi / max(total_f - 1, 1)
        t        = 2 * math.pi * fi / step_period

        # アーマチャー前進 + バウンス
        arm.location.x = orig_loc.x + walk_dir[0] * step_m * progress
        arm.location.y = orig_loc.y + walk_dir[1] * step_m * progress
        arm.location.z = orig_loc.z + bounce_amp * abs(math.sin(math.pi * fi / step_period))
        arm.keyframe_insert(data_path="location", frame=frame)

        # ボーンスイング（脚+腕）
        for bname, phase, is_knee, amp in found_bones:
            pb = arm.pose.bones.get(bname)
            if pb is None:
                continue
            pb.rotation_mode = 'XYZ'
            if is_knee:
                # 膝: 振り出し（前方スイング）時のみ曲げる。後ろへは曲げない
                pb.rotation_euler[0] = amp * max(0.0, math.sin(t + phase))
            else:
                # 大腿骨・上腕骨: X軸前後スイング（矢状面）
                pb.rotation_euler[0] = amp * math.sin(t + phase)
            pb.keyframe_insert(data_path="rotation_euler", frame=frame)

    print(f"[WalkAnim] T-poseマーチ完了: {step_m}m前進 dir={walk_dir}", flush=True)
    return True


def _apply_mixamo_action_walk(scene):
    """Mixamo Walking.fbxをZakuに適用。
    ループベーキング: scene.frame_set(looped_f)でポーズを取得しrenderフレームにベーク。
    足ボーンZ最小値を計測してアーマチャーをリフト → 下半身が地中に埋もれない。"""
    anim_cfg   = CFG.get("animation", {})
    char_cfg   = anim_cfg.get("character_motion", {})
    action_fbx = char_cfg.get("action_fbx", "")
    step_m     = float(char_cfg.get("step_length_m", 12.0))
    walk_dir   = char_cfg.get("walk_direction", [0.0, -1.0, 0.0])

    if not action_fbx or not os.path.isfile(action_fbx):
        print(f"[WalkAnim] action_fbx 見つからず: {action_fbx}", flush=True)
        return False

    char_name = CFG.get("character", {}).get("name", "")
    arm = bpy.data.objects.get(char_name) or next(
        (o for o in bpy.data.objects if o.type == "ARMATURE"), None
    )
    if arm is None:
        print("[WalkAnim] アーマチャーが見つかりません", flush=True)
        return False

    print(f"[WalkAnim] Walking.fbx 読み込み: {action_fbx}", flush=True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=action_fbx)
    src_objects = [o for o in bpy.context.scene.objects if o not in before]

    src_action = None
    for o in src_objects:
        if o.animation_data and o.animation_data.action:
            src_action = o.animation_data.action
            break
    if src_action is None and bpy.data.actions:
        src_action = list(bpy.data.actions)[-1]
    if src_action is None:
        print("[WalkAnim] ソースアクションが見つかりません", flush=True)
        return False

    src_arm = next((o for o in src_objects if o.type == "ARMATURE"), None)
    if src_arm:
        common = {b.name for b in src_arm.data.bones} & {b.name for b in arm.data.bones}
        print(f"[WalkAnim] 共通ボーン: {len(common)}本", flush=True)
        if len(common) < 15:
            print("[WalkAnim] 共通ボーン不足 → スキップ", flush=True)
            for o in src_objects:
                bpy.data.objects.remove(o, do_unlink=True)
            return False

    new_action = src_action.copy()
    new_action.name = "Zaku_Walking_Baked"
    arm.animation_data_create()
    arm.animation_data.action = new_action

    for o in src_objects:
        o.hide_set(True)
        o.hide_render = True

    total_f       = scene.frame_end - scene.frame_start + 1
    orig_loc      = arm.location.copy()
    action_start  = int(new_action.frame_range[0])
    action_end    = int(new_action.frame_range[1])
    action_length = max(1, action_end - action_start)
    root_bone_names = [b.name for b in arm.data.bones if b.parent is None]
    print(f"[WalkAnim] アクション長: {action_length}f ({action_start}-{action_end})", flush=True)

    # ── プリスキャン: ベーキング前に歩行アニメ全フレームのメッシュ最低Zを計測 ──
    # ベーキング前はnew_actionにarm.locationキーフレームがないため
    # scene.frame_set後もarm.location.z = orig_loc.z が保持される（正確に計測可能）。
    char_meshes = [c for c in arm.children_recursive if c.type == 'MESH']
    print(f"[WalkAnim] プリスキャン: {action_length}フレームのfoot-Z計測...", flush=True)
    print(f"  [DIAG] orig_loc.z={orig_loc.z:.4f}", flush=True)
    pre_min_z = float('inf')
    for pre_fi in range(action_length):
        pf = action_start + pre_fi
        scene.frame_set(pf)
        if pre_fi < 3:
            print(f"  [DIAG pf={pf}] after frame_set: arm.loc.z={arm.location.z:.4f}", flush=True)
        for bname in root_bone_names:
            pb = arm.pose.bones.get(bname)
            if pb is not None:
                pb.location = (0.0, 0.0, pb.location.z)
        bpy.context.view_layer.update()
        if pre_fi < 3:
            print(f"  [DIAG pf={pf}] after vl_update: arm.loc.z={arm.location.z:.4f}", flush=True)
        _dg = bpy.context.evaluated_depsgraph_get()
        _frame_bb_min = float('inf')   # [DIAG] bound_box最小値（参考用）
        _frame_vt_min = float('inf')   # [DIAG] vertex最小値（採用値）
        for _cm in char_meshes:
            try:
                _ev = _cm.evaluated_get(_dg)
                _mw = _ev.matrix_world
                # [DIAG] bound_box参考計測
                for _corner in _ev.bound_box:
                    _bbz = (_mw @ Vector(_corner)).z
                    if _bbz < _frame_bb_min:
                        _frame_bb_min = _bbz
                # 実頂点でボーン回転変形を含む正確な最小Z計測
                _emesh = _ev.to_mesh()
                for _v in _emesh.vertices:
                    _vz = (_mw @ _v.co).z
                    if _vz < _frame_vt_min:
                        _frame_vt_min = _vz
                _ev.to_mesh_clear()
            except Exception as _e:
                print(f"  [DIAG] to_mesh err: {_e}", flush=True)
        if _frame_vt_min < pre_min_z:
            pre_min_z = _frame_vt_min
        if pre_fi < 3:
            print(f"  [DIAG pf={pf}] bb_min={_frame_bb_min:.4f} vt_min={_frame_vt_min:.4f} pre_min_z={pre_min_z:.4f}", flush=True)
    if pre_min_z == float('inf'):
        pre_min_z = 0.437
    # 負値可: 歩行ポーズで足が浮く（pre_min_z > 0.05）場合はキャラを降下させる
    const_z_lift = 0.05 - pre_min_z
    print(f"[WalkAnim] 歩行min_foot_z={pre_min_z:.3f}m → const_z_lift={const_z_lift:.3f}m", flush=True)

    # ── ベーキングループ: ポーズ取得 + ボーンキーフレーム挿入 ─────────────────
    # arm.location はベーキングループで管理せず、_render_animation() でフレーム毎に
    # scene.frame_set() 後に直接セットする（render(animation=True) では keyframe が
    # 正しく適用されない Blender 5.1 バックグラウンドモード問題を回避）
    print(f"[WalkAnim] ベーキング ({total_f}f)...", flush=True)
    for fi in range(total_f):
        frame    = scene.frame_start + fi
        looped_f = action_start + (fi % action_length)

        scene.frame_set(looped_f)
        for bname in root_bone_names:
            pb = arm.pose.bones.get(bname)
            if pb is not None:
                pb.location = (0.0, 0.0, pb.location.z)

        for pb in arm.pose.bones:
            if pb.rotation_mode == 'QUATERNION':
                pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            else:
                pb.keyframe_insert(data_path="rotation_euler", frame=frame)
        for bname in root_bone_names:
            pb = arm.pose.bones.get(bname)
            if pb is not None:
                pb.keyframe_insert(data_path="location", frame=frame)

    # ── arm.location キーフレーム挿入（ベーキング後・scene.frame_set評価で正しく反映させる）─
    # 注意: render(animation=True)でもrender(write_still=True)でも、scene.frame_set(f)が
    # アクションのarm.locationカーブを評価してRNA値を上書きする。
    # Pythonで arm.location.z = X と設定しても view_layer.update()/render() 時に
    # アクション評価が再実行されてRNA値が戻る可能性がある。
    # 対策: arm.location自体をアクションに正しい値でキーフレーム登録し、
    # scene.frame_set(f) が自動的に正しい値を適用するようにする。
    arm_z_target  = orig_loc.z + const_z_lift
    walk_dir_v    = list(walk_dir)
    print(f"[WalkAnim] arm.locationキーフレーム挿入 ({total_f}f, arm_z={arm_z_target:.4f}m)...", flush=True)
    for fi in range(total_f):
        frame    = scene.frame_start + fi
        progress = max(0.0, min(1.0, fi / max(total_f - 1, 1)))
        arm.location.x = orig_loc.x + walk_dir_v[0] * step_m * progress
        arm.location.y = orig_loc.y + walk_dir_v[1] * step_m * progress
        arm.location.z = arm_z_target
        arm.keyframe_insert(data_path="location", frame=frame)

    # アニメーション接地グローバルに確定値を保存 → _render_animation() のDIAG用
    global _WALK_ACTIVE, _WALK_ARM_NAME, _WALK_CONST_Z, _WALK_ORIG_X, _WALK_ORIG_Y
    global _WALK_DIR, _WALK_STEP_M, _WALK_TOTAL_F, _WALK_FRAME_START
    _WALK_ACTIVE      = True
    _WALK_ARM_NAME    = arm.name
    _WALK_CONST_Z     = arm_z_target
    _WALK_ORIG_X      = orig_loc.x
    _WALK_ORIG_Y      = orig_loc.y
    _WALK_DIR         = walk_dir_v
    _WALK_STEP_M      = step_m
    _WALK_TOTAL_F     = total_f
    _WALK_FRAME_START = scene.frame_start
    print(f"[WalkAnim] 完了。ボーンベーク{total_f}f, arm_z={arm_z_target:.4f}m dir={walk_dir}", flush=True)
    return True


def _render_still():
    out_cfg  = CFG["render"]
    prefix   = out_cfg.get("output_prefix", "render")
    out_dir  = Path(out_cfg["output_dir"])
    out_path = str(out_dir / f"{prefix}_final.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[SceneBuilder] RENDER OK: {out_path}", flush=True)
    return out_path


def _render_two_pass():
    """2パスレンダー:
      Pass A - Zakuを Holdout にして背景のみ RGBA PNG で出力 (SDで写実化)
      Pass B - 通常レンダー (Zaku込み) を RGB PNG で出力 (Zakuマスク源)
    合成は post_processor.py の _composite_two_pass() で実施する。
    """
    out_cfg  = CFG["render"]
    prefix   = out_cfg.get("output_prefix", "render")
    out_dir  = Path(out_cfg["output_dir"])
    scene    = bpy.context.scene

    # キャラクター子Mesh取得
    char_name   = CFG.get("character", {}).get("name", "")
    char_obj    = bpy.data.objects.get(char_name) if char_name else None
    zaku_meshes = []
    if char_obj:
        zaku_meshes = [c for c in char_obj.children_recursive if c.type == "MESH"]

    # ── Pass A: 背景のみ（Zaku = Holdout）──────────────────────
    orig_mats = {}
    if zaku_meshes:
        holdout_mat = bpy.data.materials.new("_Holdout_Tmp")
        holdout_mat.use_nodes = True
        _hn = holdout_mat.node_tree.nodes
        _hl = holdout_mat.node_tree.links
        for _n in list(_hn):
            _hn.remove(_n)
        _ho  = _hn.new("ShaderNodeHoldout")
        _ou  = _hn.new("ShaderNodeOutputMaterial")
        _hl.new(_ho.outputs["Holdout"], _ou.inputs["Surface"])
        for mesh in zaku_meshes:
            orig_mats[mesh.name] = list(mesh.data.materials)
            mesh.data.materials.clear()
            mesh.data.materials.append(holdout_mat)

    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    bg_path = str(out_dir / f"{prefix}_bg.png")
    scene.render.filepath = bg_path
    bpy.ops.render.render(write_still=True)
    print(f"[SceneBuilder] Pass A (background) done: {prefix}_bg.png", flush=True)

    # ── Pass B: 全体レンダー（Zaku込み）────────────────────────
    if zaku_meshes:
        for mesh in zaku_meshes:
            mesh.data.materials.clear()
            for mat in orig_mats.get(mesh.name, []):
                mesh.data.materials.append(mat)
        bpy.data.materials.remove(holdout_mat)

    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    final_path = str(out_dir / f"{prefix}_final.png")
    scene.render.filepath = final_path
    bpy.ops.render.render(write_still=True)
    print(f"[SceneBuilder] Pass B (full) done: {prefix}_final.png", flush=True)
    print(f"[SceneBuilder] TWO-PASS OK: bg={prefix}_bg.png full={prefix}_final.png", flush=True)


def _render_animation():
    out_cfg = CFG["render"]
    prefix  = out_cfg.get("output_prefix", "render")
    out_dir = Path(out_cfg["output_dir"])
    scene   = bpy.context.scene

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"

    # アーマチャーオブジェクト取得（接地補正用）
    arm_obj = bpy.data.objects.get(_WALK_ARM_NAME) if _WALK_ACTIVE else None

    # フレーム毎個別レンダー:
    # arm.locationはnew_actionのキーフレームで制御（_apply_mixamo_action_walkで挿入済み）。
    # scene.frame_set(f) がアクション評価でarm.locationとボーンポーズを両方正しく設定する。
    char_meshes_r = [c for c in arm_obj.children_recursive if c.type == 'MESH'] if arm_obj else []

    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)  # arm.location + ボーンポーズをアクションから評価

        # [DIAG] arm.z + 実際の足Z計測（フレーム1と11のみ）
        if _WALK_ACTIVE and arm_obj and f in (scene.frame_start, scene.frame_start + 10):
            _az = arm_obj.location.z
            _dg_r = bpy.context.evaluated_depsgraph_get()
            _real_min_z = float('inf')
            for _cm in char_meshes_r:
                try:
                    _ev = _cm.evaluated_get(_dg_r)
                    _mw = _ev.matrix_world
                    _em = _ev.to_mesh()
                    for _v in _em.vertices:
                        _vz = (_mw @ _v.co).z
                        if _vz < _real_min_z:
                            _real_min_z = _vz
                    _ev.to_mesh_clear()
                except Exception:
                    pass
            print(f"[Render-DIAG] f={f} arm.z={_az:.4f}m  real_foot_min_z={_real_min_z:.4f}m  expected_min≈{0.05:.4f}m", flush=True)
        elif _WALK_ACTIVE and arm_obj and ((f - scene.frame_start) % 10 == 0 or f == scene.frame_end):
            print(f"[Render] f={f}/{scene.frame_end} arm.z={arm_obj.location.z:.4f}m", flush=True)

        scene.render.filepath = str(frames_dir / f"{prefix}_frame_{f:04d}")
        bpy.ops.render.render(write_still=True)

    print(f"[SceneBuilder] ANIMATION RENDER OK: {frames_dir}", flush=True)


# __ENHANCEMENT_CODE__

# ── OSM地形生成（Blender内部） ─────────────────────────────────
def _latlon_to_xy(lat, lon, lat0, lon0):
    """緯度経度をBlender XY座標(m)に変換する。"""
    dx = (lon - lon0) * math.cos(math.radians(lat0)) * 111319.0
    dy = (lat - lat0) * 111319.0
    return dx, dy


def _build_osm_terrain():
    """OSM JSONからBlenderメッシュ（建物・道路・公園）を生成する。"""
    import bmesh
    osm_path = CFG.get("terrain", {}).get("osm_json_path", "")
    if not osm_path or not os.path.isfile(osm_path):
        print("[TerrainBuilder] OSM JSON not found, skipping terrain", flush=True)
        return

    with open(osm_path, encoding="utf-8") as f:
        osm = json.load(f)

    meta     = osm.get("_meta", {})
    lat0     = meta.get("center_lat", 35.6580)
    lon0     = meta.get("center_lon", 139.7016)
    margin   = meta.get("margin_m", 500)
    elements = osm.get("elements", [])

    mat_cfg   = CFG.get("materials", {})
    roughness = mat_cfg.get("roughness_override", 0.7)

    # 地面プレーン（ダークアスファルト：clear+appendで確実に設定）
    bpy.ops.mesh.primitive_plane_add(size=margin * 2, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "OSM_Ground"
    # 既存マテリアルをクリアしてから追加（Blender5.1 slot挙動対策）
    ground.data.materials.clear()
    _ground_dark = _make_dark_asphalt_mat()
    ground.data.materials.append(_ground_dark)
    print("[TerrainBuilder] Ground: OSM_Dark_Asphalt applied via _make_dark_asphalt_mat()", flush=True)

    # PBRマテリアル（AmbientCGなければグレーフォールバック）
    bldg_mat = _pbr_from_ambientcg(mat_cfg.get("building_texture", "Concrete034"), roughness)
    if bldg_mat is None:
        bldg_mat = _get_or_make_mat("OSM_Building_Default")
        bldg_mat.use_nodes = True
        _bsdf = next((n for n in bldg_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if _bsdf is None:
            _bsdf = bldg_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        _bsdf.inputs["Base Color"].default_value = (0.60, 0.58, 0.55, 1.0)  # コンクリートグレー
        _bsdf.inputs["Roughness"].default_value  = 0.8
    # 建物マテリアルが確定したタイミングで窓グリッドを追加
    _add_window_overlay(bldg_mat)

    road_mat = _pbr_from_ambientcg(mat_cfg.get("road_texture", "Ground079S"), roughness + 0.1)
    if road_mat is None:
        road_mat = _get_or_make_mat("OSM_Road_Default")
        road_mat.use_nodes = True
        _rbsdf = next((n for n in road_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if _rbsdf is None:
            _rbsdf = road_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        _rbsdf.inputs["Base Color"].default_value = (0.20, 0.20, 0.20, 1.0)  # アスファルト
        _rbsdf.inputs["Roughness"].default_value  = 0.95

    bldg_count = 0
    road_count = 0

    for elem in elements:
        if elem.get("type") != "way":
            continue
        geometry = elem.get("geometry", [])
        if len(geometry) < 3:
            continue

        tags        = elem.get("tags", {})
        is_building = bool(tags.get("building"))
        is_road     = bool(tags.get("highway"))
        is_park     = tags.get("landuse") in ("park", "grass", "recreation_ground")

        verts_2d = [_latlon_to_xy(pt["lat"], pt["lon"], lat0, lon0) for pt in geometry]
        if len(verts_2d) > 1 and verts_2d[0] == verts_2d[-1]:
            verts_2d = verts_2d[:-1]
        if len(verts_2d) < 3:
            continue

        # ザク立ち位置(0,0)に重なる建物をスキップ（ザクが建物内に埋まるのを防ぐ）
        if is_building:
            cx_b = sum(x for x, y in verts_2d) / len(verts_2d)
            cy_b = sum(y for x, y in verts_2d) / len(verts_2d)
            min_x = min(x for x, y in verts_2d)
            max_x = max(x for x, y in verts_2d)
            min_y = min(y for x, y in verts_2d)
            max_y = max(y for x, y in verts_2d)
            # 建物のBBoxが原点から20m以内に入っている場合はスキップ
            if min_x < 20 and max_x > -20 and min_y < 20 and max_y > -20:
                if abs(cx_b) < 30 and abs(cy_b) < 30:
                    continue

        if is_building:
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

            bm = bmesh.new()
            for x, y in verts_2d:
                bm.verts.new((x, y, 0.0))
            bm.verts.ensure_lookup_table()
            try:
                # convex_hull で凹型・複雑形状も対応
                bmesh.ops.convex_hull(bm, input=bm.verts)
                faces = [f for f in bm.faces]
                if not faces:
                    raise ValueError("no faces from convex_hull")
                # 法線を上向きに統一
                bmesh.ops.recalc_face_normals(bm, faces=faces)
                # 上面を押し出してから translate で高さ分だけ移動（z>0.01判定は無効）
                ext = bmesh.ops.extrude_face_region(bm, geom=faces)
                top_verts = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
                bmesh.ops.translate(bm, verts=top_verts, vec=(0.0, 0.0, height))
                # 底面フェース(z≈0)を削除してOSM_Groundを露出させる
                bottom_faces = [f for f in bm.faces if all(v.co.z < 0.01 for v in f.verts)]
                if bottom_faces:
                    bmesh.ops.delete(bm, geom=bottom_faces, context='FACES')
                bm.normal_update()
                mesh = bpy.data.meshes.new(f"OSM_Building_{bldg_count}")
                bm.to_mesh(mesh)
                bm.free()
                obj = bpy.data.objects.new(f"OSM_Building_{bldg_count}", mesh)
                bpy.context.collection.objects.link(obj)
                if bldg_mat:
                    obj.data.materials.append(bldg_mat)          # slot 0: 壁面
                    _roof_mat = _make_dark_asphalt_mat()
                    obj.data.materials.append(_roof_mat)          # slot 1: 屋上
                    for poly in obj.data.polygons:
                        if poly.normal.z > 0.5:                   # 上向きフェース=屋上
                            poly.material_index = 1
                # 影を落とさない（地面が暗くなるのを防ぐ）
                obj.visible_shadow = False
                bldg_count += 1
            except Exception:
                bm.free()

        elif is_road:
            bm = bmesh.new()
            verts = [bm.verts.new((x, y, 0.01)) for x, y in verts_2d]
            for i in range(len(verts) - 1):
                bm.edges.new((verts[i], verts[i + 1]))
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
            for x, y in verts_2d:
                bm.verts.new((x, y, 0.02))
            bm.verts.ensure_lookup_table()
            try:
                bmesh.ops.convex_hull(bm, input=bm.verts)
                if not bm.faces:
                    raise ValueError("no faces")
                bm.normal_update()
                mesh = bpy.data.meshes.new(f"OSM_Park_{bldg_count}")
                bm.to_mesh(mesh)
                bm.free()
                obj = bpy.data.objects.new(f"OSM_Park_{bldg_count}", mesh)
                bpy.context.collection.objects.link(obj)
                park_mat = _get_or_make_mat("Park_Mat")
                park_mat.use_nodes = True
                _bsdf = next((n for n in park_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if _bsdf:
                    _bsdf.inputs["Base Color"].default_value = (0.15, 0.45, 0.15, 1.0)
                    _bsdf.inputs["Roughness"].default_value  = 0.95
                obj.data.materials.append(park_mat)
            except Exception:
                bm.free()

    # 道路白線オーバーレイ（hide_renderで非表示 — BsdfTransparentがBlender5.1で不透明化する問題を回避）
    _add_road_markings()
    _rm_obj = bpy.data.objects.get("Road_Markings")
    if _rm_obj:
        _rm_obj.hide_render = True
        print("[TerrainBuilder] Road_Markings: hide_render=True (BsdfTransparent workaround)", flush=True)

    print(f"[TerrainBuilder] OSM mesh: {bldg_count} buildings, {road_count} roads", flush=True)


# ── メイン実行 ──────────────────────────────────────────────────
import traceback
_completed_steps = []
try:
    print("[SceneBuilder] === START ===", flush=True)

    # ── blendソース読み込み ──
    blend_src = CFG.get("blend_source", "")
    if blend_src and os.path.isfile(blend_src):
        bpy.ops.wm.open_mainfile(filepath=blend_src)
        print(f"[SceneBuilder] Blend loaded: {os.path.basename(blend_src)}", flush=True)
    else:
        print("[SceneBuilder] No blend_source, using empty scene", flush=True)

    # ── OSM地形生成（data_source == "osm" の場合） ──
    terrain_src = CFG.get("terrain", {}).get("data_source", "blend_only")
    if terrain_src == "osm":
        _build_osm_terrain()
        _add_traffic_lights()
        _completed_steps.append("terrain_osm")

    # ── キャラクター取得（既存シーン優先 → FBXインポートフォールバック） ──
    char_cfg  = CFG.get("character", {})
    char_name = char_cfg.get("name", "")
    height_m  = char_cfg.get("height_m", 18.0)

    def _find_character():
        """シーン内からキャラクターオブジェクトを検索する。"""
        # 正確な名前一致
        if char_name and char_name in bpy.data.objects:
            return bpy.data.objects[char_name]
        # 部分一致（大文字小文字無視）
        keywords = [char_name.lower()] if char_name else []
        keywords += ["zaku", "dom", "guncannon", "gundam", "character", "armature"]
        for obj in bpy.context.scene.objects:
            nl = obj.name.lower()
            if any(k in nl for k in keywords if k):
                return obj
        return None

    char_obj = _find_character()

    if char_obj is not None:
        print(f"[SceneBuilder] Character found in scene: {char_obj.name}", flush=True)
        _completed_steps.append("character_import")
    else:
        # FBXインポートを試みる
        fbx_path = char_cfg.get("fbx_path", "")
        if fbx_path and os.path.isfile(fbx_path):
            bpy.ops.import_scene.fbx(filepath=fbx_path,
                                      use_anim=True,
                                      automatic_bone_orientation=True)
            bpy.context.view_layer.update()
            imported = list(bpy.context.selected_objects)
            armature = next((o for o in imported if o.type == "ARMATURE"), None)
            if armature is None and imported:
                armature = imported[0]
            if armature:
                if char_name:
                    armature.name = char_name
                # ポーズリセット: FBXのデフォルトポーズ（屈み等）を直立Tポーズに戻す
                if armature.type == "ARMATURE":
                    bpy.context.view_layer.objects.active = armature
                    bpy.ops.object.mode_set(mode='POSE')
                    for _pb in armature.pose.bones:
                        _pb.location = (0, 0, 0)
                        _pb.rotation_quaternion = (1, 0, 0, 0)
                        _pb.rotation_euler = (0, 0, 0)
                        _pb.scale = (1, 1, 1)
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.context.view_layer.update()
                    print(f"[SceneBuilder] Pose reset to T-pose (rest)", flush=True)
                # スケーリング: mesh children BBoxで測定（armature.bound_boxは常に空/無効）
                bpy.context.view_layer.update()
                _fbx_meshes = [o for o in armature.children_recursive if o.type == "MESH"]
                if not _fbx_meshes:
                    _fbx_meshes = [o for o in imported if o.type == "MESH"]
                if _fbx_meshes:
                    import mathutils as _mu
                    _dg = bpy.context.evaluated_depsgraph_get()
                    _zv = []
                    for _m in _fbx_meshes:
                        _src = _m.evaluated_get(_dg)
                        for _c in _src.bound_box:
                            _zv.append((_src.matrix_world @ _mu.Vector(_c)).z)
                    current_h = max(_zv) - min(_zv) if len(_zv) > 1 else 0.0
                else:
                    current_h = 0.0
                if current_h > 0.01:
                    _sf = height_m / current_h
                    armature.scale = tuple(s * _sf for s in armature.scale)
                    bpy.context.view_layer.update()
                    print(f"[SceneBuilder] FBX scaled: {current_h:.3f}→{height_m}m (x{_sf:.5f})", flush=True)
                else:
                    print(f"[SceneBuilder] FBX scale: mesh not found, skipping scale", flush=True)
                # 原点に配置
                armature.location = (0.0, 0.0, 0.0)
                bpy.context.view_layer.update()
                # グラウンディング: 足元をz=0に合わせる
                if _fbx_meshes:
                    import mathutils as _mug
                    _dg_g = bpy.context.evaluated_depsgraph_get()
                    _gz_all = []
                    for _mg in _fbx_meshes:
                        _mg_ev = _mg.evaluated_get(_dg_g)
                        for _cg in _mg_ev.bound_box:
                            _gz_all.append((_mg_ev.matrix_world @ _mug.Vector(_cg)).z)
                    if _gz_all:
                        _foot_z = min(_gz_all)
                        if abs(_foot_z) > 0.01 or _foot_z < 0.04:
                            # 足底をz=+0.05mに置く（0.0だとground plane=0と面一でZ-fightingが発生）
                            armature.location.z -= _foot_z - 0.05
                            bpy.context.view_layer.update()
                            print(f"[SceneBuilder] FBX grounded: foot {_foot_z:.3f}→z=0.05 (+5cm Z-fight防止)", flush=True)
                char_obj = armature
                print(f"[SceneBuilder] FBX imported: {armature.name}", flush=True)
                _completed_steps.append("character_import")
        else:
            print(f"[SceneBuilder] Character not found in scene, FBX missing: {fbx_path}", flush=True)

    # ライティング
    hdri = CFG["lighting"].get("hdri_path","")
    if hdri and os.path.isfile(hdri):
        _hdri_world(hdri)
    else:
        _procedural_sky()
    _setup_sun()
    _setup_fill_lights()
    _add_sky_ambient()
    # 大気散乱（無効化済み）
    _setup_volumetric_atmosphere()
    _completed_steps.append("lighting")

    # マテリアル強化
    _enhance_materials()
    # OSM地面プレーンの確認（OSM_Ground_Darkが維持されているかチェック）
    for _g_obj in bpy.context.scene.objects:
        if _g_obj.type == "MESH" and "osm_ground" in _g_obj.name.lower():
            _slot_mat = _g_obj.material_slots[0].material.name if _g_obj.material_slots and _g_obj.material_slots[0].material else "None"
            _data_mat = _g_obj.data.materials[0].name if _g_obj.data.materials else "None"
            print(f"[SceneBuilder] {_g_obj.name}: slot={_slot_mat} data={_data_mat}", flush=True)
    # キャラクター金属PBR（enhance_materials後に適用してArmature子Meshを確実に取得）
    _apply_metal_pbr(char_obj)
    _completed_steps.append("materials")

    # 接地AO（char_objを直接渡す）
    _setup_contact_ao(char_obj=char_obj)
    _completed_steps.append("contact_ao")

    # カメラ（キャラクターの実際の座標に自動追従）
    _setup_camera(char_obj=char_obj)
    _completed_steps.append("camera")

    # 被写界深度（カメラ設定後）
    _setup_dof(char_obj=char_obj)
    _completed_steps.append("dof")

    # レンダー設定
    _setup_render()

    # AgX色管理 + コンポジター効果（レンダー設定後）
    try:
        _setup_color_management()
    except Exception as _ce:
        print(f"[SceneBuilder] Color management skipped: {_ce}", flush=True)
    _setup_compositor_effects()  # 内部でtry/except済み
    _completed_steps.append("postfx")

    # アニメーション
    if CFG.get("animation",{}).get("enabled", False):
        _setup_animation()
        _render_animation()
    elif CFG.get("render", {}).get("two_pass", False):
        _render_two_pass()
    else:
        _render_still()
    _completed_steps.append("render")

    # 結果をJSONに保存
    result = {
        "status": "ok",
        "output": CFG["render"]["output_dir"],
        "completed_steps": _completed_steps,
        "errors": [],
        "warnings": [],
    }
    result_path = Path(CFG["render"]["output_dir"]) / "build_result.json"
    result_path.write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[SceneBuilder] === DONE ===", flush=True)

except Exception as e:
    err_result = {
        "status": "error",
        "completed_steps": _completed_steps,
        "errors": [str(e)],
        "warnings": [],
    }
    result_path = Path(CFG["render"]["output_dir"]) / "build_result.json"
    try:
        result_path.write_text(__import__("json").dumps(err_result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    print(f"[SceneBuilder] FATAL: {e}", flush=True)
    traceback.print_exc()
'''


def generate_blender_script(config: dict) -> str:
    """YAMLコンフィグからBlender実行用Pythonスクリプトを生成する。"""
    import json
    from material_enhancements import get_injection_code, merge_params as _me_merge

    cfg_json    = json.dumps(config, ensure_ascii=True)
    cfg_escaped = cfg_json.replace("\\", "\\\\").replace('"', '\\"')

    enh_params = _me_merge(config.get("city_enhancements"))
    injection  = get_injection_code(enh_params)

    script = _BLENDER_SCRIPT.replace("__CFG__", cfg_escaped)
    return script.replace("# __ENHANCEMENT_CODE__", injection)
