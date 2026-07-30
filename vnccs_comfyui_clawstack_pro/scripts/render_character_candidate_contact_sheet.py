import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fbx", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def world_bounds(objects):
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    return minimum, maximum


def normalize_character_scale(meshes):
    minimum, maximum = world_bounds(meshes)
    source_height = maximum.z - minimum.z
    if source_height <= 0:
        return 1.0
    factor = 1.75 / source_height
    roots = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    for obj in roots:
        obj.scale *= factor
    bpy.context.view_layer.update()
    return factor


def setup_scene(minimum, maximum):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("CandidateQAWorld")
    scene.world.color = (0.018, 0.022, 0.032)

    center = (minimum + maximum) * 0.5
    height = max(0.1, maximum.z - minimum.z)
    width = max(maximum.x - minimum.x, maximum.y - minimum.y)
    distance = max(height * 2.2, width * 3.0)

    bpy.ops.object.camera_add(location=(center.x, center.y - distance, center.z + height * 0.02))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(height * 1.14, width * 1.35)
    camera.data.clip_start = max(0.001, height * 0.01)
    camera.data.clip_end = height * 100
    point_at(camera, center + Vector((0, 0, height * 0.02)))
    scene.camera = camera

    for name, location, energy, size in (
        ("Key", center + Vector((height * 1.4, -height * 1.5, height * 1.8)), 700, height * 1.5),
        ("Fill", center + Vector((-height * 1.5, -height * 0.7, height * 0.8)), 350, height * 1.2),
        ("Rim", center + Vector((0, height * 1.2, height * 1.6)), 550, height),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point_at(light, center)

    floor_z = minimum.z - height * 0.01
    bpy.ops.mesh.primitive_plane_add(size=max(height, width) * 4, location=(center.x, center.y, floor_z))
    floor = bpy.context.object
    floor.name = "QA_Floor"
    mat = bpy.data.materials.new("QA_Floor_Material")
    mat.diffuse_color = (0.035, 0.045, 0.065, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.035, 0.045, 0.065, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.72
    floor.data.materials.append(mat)


def inspect_candidate(path, output_dir, index):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True, use_custom_normals=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes:
        return {"file": str(path), "error": "no_mesh"}

    scale_factor = normalize_character_scale(meshes)
    minimum, maximum = world_bounds(meshes)
    setup_scene(minimum, maximum)
    scene = bpy.context.scene
    actions = list(bpy.data.actions)
    if actions:
        start, end = actions[0].frame_range
        scene.frame_set(int(start + (end - start) * 0.25))

    stem = f"{index:02d}_{path.stem}"
    full_path = output_dir / f"{stem}_full.png"
    scene.render.filepath = str(full_path)
    bpy.ops.render.render(write_still=True)

    material_names = sorted({
        slot.material.name
        for obj in meshes
        for slot in obj.material_slots
        if slot.material
    })
    return {
        "file": str(path),
        "preview": str(full_path),
        "meshes": len(meshes),
        "triangles": sum(
            sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
            for obj in meshes
        ),
        "armatures": len(rigs),
        "bones": sum(len(rig.data.bones) for rig in rigs),
        "actions": len(actions),
        "materials": len(material_names),
        "qa_scale_factor": scale_factor,
        "bounds": {
            "minimum": list(minimum),
            "maximum": list(maximum),
        },
    }


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [
        inspect_candidate(Path(value).resolve(), output_dir, index)
        for index, value in enumerate(args.fbx, start=1)
    ]
    report = {
        "purpose": "visual_candidate_comparison_only",
        "results": results,
    }
    report_path = output_dir / "candidate_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
