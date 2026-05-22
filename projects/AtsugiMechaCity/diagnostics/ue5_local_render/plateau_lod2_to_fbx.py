"""
plateau_lod2_to_fbx.py  — Blender headless で実行

plateau_lod2_radius100.json を読み込み、
LOD2 建物メッシュ＋テクスチャを Blender シーンに構築して FBX エクスポートする。

使い方:
  blender --background --python plateau_lod2_to_fbx.py

出力:
  plateau_lod2_buildings_radius100.fbx  (テクスチャを相対パス参照)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
from pathlib import Path

import bpy
import bmesh

# -----------------------------------------------------------------------
# パス設定
# -----------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
JSON_PATH  = SCRIPT_DIR / "plateau_lod2_radius100.json"
FBX_OUT    = SCRIPT_DIR / "plateau_lod2_buildings_radius100.fbx"

GREY_MAT_NAME = "PLATEAU_LOD2_NoTexture"

def log(msg):
    print(f"[LOD2toFBX] {msg}")

# -----------------------------------------------------------------------
# マテリアル作成
# -----------------------------------------------------------------------
_mat_cache: dict = {}

def get_or_create_material(texture_path: str | None) -> bpy.types.Material:
    key = texture_path or "__grey__"
    if key in _mat_cache:
        return _mat_cache[key]

    if texture_path is None:
        mat = bpy.data.materials.new(GREY_MAT_NAME)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.50, 0.50, 0.50, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.85
    else:
        tex_p = Path(texture_path)
        mat_name = "TEX_" + tex_p.stem
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        bsdf = nodes.get("Principled BSDF")

        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.location = (-300, 300)
        if tex_p.exists():
            img = bpy.data.images.load(str(tex_p))
            tex_node.image = img
        else:
            log(f"  WARNING: texture not found: {texture_path}")

        if bsdf:
            links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
            bsdf.inputs["Roughness"].default_value = 0.80

    _mat_cache[key] = mat
    return mat

# -----------------------------------------------------------------------
# 建物メッシュ構築
# -----------------------------------------------------------------------
def build_building(bldg_data: dict) -> bpy.types.Object | None:
    bldg_id = bldg_data["id"]
    faces_data = bldg_data["faces"]
    if not faces_data:
        return None

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # テクスチャ → マテリアルインデックス マッピング
    tex_to_mat_idx: dict = {}
    mat_list: list = []

    face_ok = 0
    face_skip = 0

    for face_data in faces_data:
        tex_path = face_data.get("texture_path")
        verts_xyz = face_data["vertices"]
        uvs = face_data["uvs"]

        if len(verts_xyz) < 3:
            face_skip += 1
            continue

        # マテリアルインデックス確定
        key = tex_path or "__grey__"
        if key not in tex_to_mat_idx:
            tex_to_mat_idx[key] = len(mat_list)
            mat_list.append(get_or_create_material(tex_path))
        mat_idx = tex_to_mat_idx[key]

        # bmesh に頂点追加
        bm_verts = []
        for xyz in verts_xyz:
            v = bm.verts.new((xyz[0], xyz[1], xyz[2]))
            bm_verts.append(v)

        try:
            face = bm.faces.new(bm_verts)
            face.material_index = mat_idx
            # UV 設定
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = (float(uv[0]), float(uv[1]))
            face_ok += 1
        except ValueError:
            face_skip += 1
            # 重複頂点は bmesh から除去してリトライ
            for v in bm_verts:
                bm.verts.remove(v)
            continue

    if face_ok == 0:
        bm.free()
        return None

    bm.normal_update()

    mesh = bpy.data.meshes.new(bldg_id)
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()

    obj = bpy.data.objects.new(bldg_id, mesh)
    bpy.context.scene.collection.objects.link(obj)

    for mat in mat_list:
        obj.data.materials.append(mat)

    return obj

# -----------------------------------------------------------------------
# メイン
# -----------------------------------------------------------------------
def main():
    log(f"Loading JSON: {JSON_PATH}")
    if not JSON_PATH.exists():
        log("ERROR: JSON not found. Run plateau_lod2_extract.py first.")
        sys.exit(1)

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # シーンクリア
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)

    # 単位設定: メートル
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    buildings = data["buildings"]
    log(f"Processing {len(buildings)} buildings ...")

    ok_count = 0
    for i, bldg in enumerate(buildings):
        obj = build_building(bldg)
        if obj:
            ok_count += 1
        if (i + 1) % 10 == 0:
            log(f"  {i + 1}/{len(buildings)} done")

    log(f"Built {ok_count} building objects")
    log(f"Materials: {len(_mat_cache)}")

    # FBX エクスポート
    log(f"Exporting FBX: {FBX_OUT}")
    bpy.ops.export_scene.fbx(
        filepath=str(FBX_OUT),
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Y",
        axis_up="Z",
        object_types={"MESH"},
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        path_mode="COPY",          # テクスチャを FBX と同ディレクトリにコピー
        embed_textures=False,
        bake_anim=False,
    )

    log(f"Done. FBX saved: {FBX_OUT}")
    log(f"Texture files alongside FBX in: {FBX_OUT.parent}")

main()
