
import bpy, math, os, glob, json, random
from pathlib import Path
from mathutils import Vector, Euler

CFG      = json.loads("{\"scene\": {\"name\": \"hon_atsugi_dom\", \"description\": \"\\u672c\\u539a\\u6728\\u99c5\\u524d\\u5e83\\u5834\\u306bDOM\\u3092\\u914d\\u7f6e\\u3002PLATEAU + Mixamo\\u30dd\\u30fc\\u30ba\\u3002\"}, \"blend_source\": \"D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/Hon_Atsugi_Station_Plateau_Mecha.blend\", \"terrain\": {\"obj_path\": \"D:/Clawdbot_Docker_20260125/apps/agi_designer/viewer/exports/Atsugi_Terrain.obj\", \"plateau_gml_dir\": \"D:/Clawdbot_Docker_20260125/data/PLATEAU/Atsugi/udx\", \"coordinate_system\": \"EPSG:6668\"}, \"character\": {\"fbx_path\": \"D:/Clawdbot_Docker_20260125/Gundam/FLB/DOM_RIG_Mixamo.fbx\", \"name\": \"Zaku_Armature\", \"height_m\": 18.0, \"position\": {\"lat\": 35.4437, \"lon\": 139.413}, \"grounding\": {\"enabled\": true, \"embed_depth\": 0.75, \"contact_pad\": true}, \"pose_fbx\": \"D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/diagnostics/dom_mixamo_walk/DOM_Mixamo_Walk_Preview.blend\"}, \"camera\": {\"position\": [0.0, -35.0, 6.0], \"target\": [0.0, 0.0, 9.0], \"lens_mm\": 85, \"resolution\": [1920, 1080]}, \"lighting\": {\"hdri_path\": \"\", \"hdri_strength\": 1.0, \"sun\": {\"enabled\": true, \"lat\": 35.4437, \"lon\": 139.413, \"hour\": 14, \"energy\": 6.0}, \"fill_lights\": [{\"type\": \"AREA\", \"position\": [-15, -20, 10], \"energy\": 300, \"color\": [0.95, 0.97, 1.0]}, {\"type\": \"AREA\", \"position\": [15, -10, 5], \"energy\": 150, \"color\": [1.0, 0.95, 0.88]}]}, \"materials\": {\"ambientcg_dir\": \"D:/Clawdbot_Docker_20260125/data/workspace/apps/blender_assets/ambientcg\", \"building_texture\": \"Concrete034\", \"road_texture\": \"Ground079S\", \"metal_texture\": \"Metal027\", \"roughness_override\": 0.65, \"apply_to_existing\": true}, \"contact_ao\": {\"enabled\": true, \"radius\": 4.0, \"strength\": 0.7, \"shadow_catcher\": true}, \"render\": {\"engine\": \"CYCLES\", \"device\": \"CPU\", \"samples\": 64, \"denoiser\": \"OPENIMAGEDENOISE\", \"output_dir\": \"D:/Clawdbot_Docker_20260125/projects/CityCharacterPipeline/output/hon_atsugi_dom\", \"output_prefix\": \"hon_atsugi_dom\"}, \"animation\": {\"enabled\": false, \"fps\": 24, \"total_frames\": 120, \"camera_motion\": {\"type\": \"orbit\", \"orbit_radius\": 40.0, \"orbit_z\": 8.0}, \"character_motion\": {\"type\": \"idle\", \"action_fbx\": \"\"}}, \"knowledge\": {\"record_to_db\": true, \"record_to_brv\": true, \"project_tag\": \"hon_atsugi_dom\"}}")
OUT_DIR  = Path(CFG["render"]["output_dir"])
OUT_DIR.mkdir(parents=True, exist_ok=True)
PREFIX   = CFG["render"]["output_prefix"]
AMCG_DIR = Path(CFG["materials"]["ambientcg_dir"])


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

    def _tex(path, colorspace="sRGB"):
        t = nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        t.image.colorspace_settings.name = colorspace
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


def _enhance_materials():
    """既存マテリアルをPBRに強化する。建物・道路・金属を識別して適用。"""
    mat_cfg  = CFG["materials"]
    roughness = mat_cfg.get("roughness_override", 0.7)

    bldg_mat  = _pbr_from_ambientcg(mat_cfg.get("building_texture","Concrete034"), roughness)
    road_mat  = _pbr_from_ambientcg(mat_cfg.get("road_texture","Ground079S"), roughness + 0.1)
    metal_mat = _pbr_from_ambientcg(mat_cfg.get("metal_texture","Metal027"), roughness - 0.2)

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
        # キャラクター子Mesh・AO系はスキップ
        if obj.name in char_mesh_ids:
            continue
        if any(k in name_l for k in ("contact_ao","shadow","preview_ground")):
            continue
        # マテリアル分類
        if any(k in name_l for k in ("bldg","building","wall","house","tower")):
            target = bldg_mat
        elif any(k in name_l for k in ("road","tran","street","walk","crosswalk")):
            target = road_mat
        elif any(k in name_l for k in ("metal","steel","pipe","rail","corrugated")):
            target = metal_mat
        else:
            target = bldg_mat  # デフォルト: コンクリート

        if target is None:
            _ensure_principled(obj, roughness)
            continue
        if obj.data.materials:
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
        else:
            loc = char_obj.matrix_world.translation
            cx, cy, foot_z = loc.x, loc.y, loc.z
            height = 0.0
        # 公式全高テーブルでフォールバック
        if height < 1.0:
            height = _lookup_height_m(char_obj.name,
                                      CFG.get("character",{}).get("height_m", 18.0))
        # カメラをキャラ前方 height*2.5 + 斜め上から狙う（85mm望遠相当）
        dist  = height * 2.5
        cam_z = foot_z + height * 0.35
        pos = (cx, cy - dist, cam_z)
        tgt = (cx, cy, foot_z + height * 0.55)
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

    scene = bpy.context.scene
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    print(f"[SceneBuilder] Camera: pos=({pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}), lens={lens}mm", flush=True)


def _setup_render():
    ren_cfg = CFG["render"]
    scene   = bpy.context.scene
    scene.render.engine = ren_cfg.get("engine","CYCLES")
    scene.cycles.device = ren_cfg.get("device","CPU")
    scene.cycles.samples = ren_cfg.get("samples", 64)
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = ren_cfg.get("denoiser","OPENIMAGEDENOISE")
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    print(f"[SceneBuilder] Render: {scene.render.engine} {scene.cycles.samples}spp", flush=True)


def _setup_animation():
    anim_cfg = CFG.get("animation", {})
    if not anim_cfg.get("enabled", False):
        return
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end   = anim_cfg.get("total_frames", 120)
    scene.render.fps  = anim_cfg.get("fps", 24)

    cam_motion = anim_cfg.get("camera_motion", {})
    if cam_motion.get("type") == "orbit":
        cam = bpy.context.scene.camera
        if cam is None:
            return
        r = cam_motion.get("orbit_radius", 30.0)
        z = cam_motion.get("orbit_z", 6.0)
        total = scene.frame_end - scene.frame_start + 1
        for f in range(scene.frame_start, scene.frame_end + 1):
            angle = 2 * math.pi * (f - scene.frame_start) / total
            cam.location = (r * math.sin(angle), -r * math.cos(angle), z)
            cam.keyframe_insert("location", frame=f)
            import mathutils
            tgt = mathutils.Vector(CFG["camera"].get("target",[0,0,9]))
            direction = (tgt - cam.location).normalized()
            cam.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()
            cam.keyframe_insert("rotation_euler", frame=f)
    print(f"[SceneBuilder] Animation: {scene.frame_end}frames, cam={cam_motion.get('type')}", flush=True)


def _render_still():
    out_cfg = CFG["render"]
    prefix  = out_cfg.get("output_prefix","render")
    out_dir = Path(out_cfg["output_dir"])
    out_path = str(out_dir / f"{prefix}_final.png")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[SceneBuilder] RENDER OK: {out_path}", flush=True)
    return out_path


def _render_animation():
    out_cfg  = CFG["render"]
    prefix   = out_cfg.get("output_prefix","render")
    out_dir  = Path(out_cfg["output_dir"]) / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(out_dir / f"{prefix}_frame_")
    bpy.ops.render.render(animation=True)
    print(f"[SceneBuilder] ANIMATION RENDER OK: {out_dir}", flush=True)


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
                # スケーリング: blendシーンの単位に合わせる
                bpy.context.view_layer.update()
                bbox = [armature.matrix_world @ Vector(c) for c in armature.bound_box]
                current_h = max(v.z for v in bbox) - min(v.z for v in bbox)
                if current_h > 0.01:
                    scale = height_m / current_h
                    armature.scale = (scale, scale, scale)
                    bpy.context.view_layer.update()
                # 原点に配置（grounding後にZ調整）
                armature.location = (0.0, 0.0, 0.0)
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
    _completed_steps.append("lighting")

    # マテリアル強化
    _enhance_materials()
    _completed_steps.append("materials")

    # 接地AO（char_objを直接渡す）
    _setup_contact_ao(char_obj=char_obj)
    _completed_steps.append("contact_ao")

    # カメラ（キャラクターの実際の座標に自動追従）
    _setup_camera(char_obj=char_obj)
    _completed_steps.append("camera")

    # レンダー設定
    _setup_render()

    # アニメーション
    if CFG.get("animation",{}).get("enabled", False):
        _setup_animation()
        _render_animation()
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
