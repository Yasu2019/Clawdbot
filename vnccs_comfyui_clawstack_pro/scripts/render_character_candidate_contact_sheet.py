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


def setup_scene(minimum, maximum):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.018, 0.022, 0.032)

    center = (minimum + maximum) * 0.5
    height = max(0.1, maximum.z - minimum.z)
    width = max(maximum.x - minimum.x, maximum.y - minimum.y)
    distance = max(height * 1.45, width * 2.4)

    bpy.ops.object.camera_add(location=(center.x + distance * 0.48, center.y - distance, center.z + height * 0.04))
    camera = bpy.context.object
    camera.data.lens = 62
    point_at(camera, center + Vector((0, 0, height * 0.02)))
    scene.camera = camera

    for name, location, energy, size in (
        ("Key", center + Vector((height * 1.4, -height * 1.5, height * 1.8)), 1150, height * 1.5),
        ("Fill", center + Vector((-height * 1.5, -height * 0.7, height * 0.8)), 700, height * 1.2),
        ("Rim", center + Vector((0, height * 1.2, height * 1.6)), 950, height),
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
