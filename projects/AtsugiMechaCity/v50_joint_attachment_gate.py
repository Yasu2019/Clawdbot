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


TORSO = [
    "Torso_Core", "Pelvis_Center", "geometry_0", "geometry_0.001", "geometry_0.003",
    "geometry_0.004", "geometry_0.007", "geometry_0.010", "geometry_0.011", "geometry_0.015",
    "V50_RENDER_ShoulderSocket_L", "V50_RENDER_ShoulderSocket_R",
]
UPPER_ARM_L = ["geometry_0.012", "geometry_0.018", "geometry_0.020", "geometry_0.034"]
# INC-140: geometry_0.005 moved from HAND_L to LOWER_ARM_L to match rig semantics
# (it is the distal forearm mesh spanning elbow->wrist). Keeping it on the child
# side made the wrist_L parent look detached even in the accepted original layout.
LOWER_ARM_L = ["geometry_0.023", "geometry_0.032", "geometry_0.005"]
HAND_L = [
    # V50 has no stable independent left-hand mesh; QA uses proxies/render hands.
    "V50_RENDER_Hand_L_Palm", "V50_RENDER_Hand_L_Core",
    "V50_RENDER_Hand_L_Finger_A", "V50_RENDER_Hand_L_Finger_B", "V50_RENDER_Hand_L_Finger_C",
    "V50_PROXY_Hand_L_Palm", "V50_PROXY_Hand_L_Palm_Core",
    "V50_PROXY_Hand_L_Finger_A", "V50_PROXY_Hand_L_Finger_B", "V50_PROXY_Hand_L_Finger_C",
]
UPPER_ARM_R = ["geometry_0.002", "geometry_0.019", "geometry_0.021", "geometry_0.022"]
LOWER_ARM_R = ["geometry_0.024", "geometry_0.033"]
HAND_R = ["geometry_0.006"]

UPPER_LEG_L = ["UpperLeg_L", "UpperLegCore_L"]
LOWER_LEG_L = ["geometry_0.016", "geometry_0.027"]
FOOT_L = ["geometry_0.013", "geometry_0.030", "geometry_0.025", "geometry_0.008"]
UPPER_LEG_R = ["UpperLeg_R", "UpperLegCore_R"]
LOWER_LEG_R = ["geometry_0.017", "geometry_0.028"]
FOOT_R = ["geometry_0.014", "geometry_0.031", "geometry_0.026", "geometry_0.029", "geometry_0.009"]

MARKERS = {
    "shoulder_L": "V50_RIG_MARKER_shoulder_L",
    "elbow_L": "V50_RIG_MARKER_elbow_L",
    "wrist_L": "V50_RIG_MARKER_wrist_L",
    "shoulder_R": "V50_RIG_MARKER_shoulder_R",
    "elbow_R": "V50_RIG_MARKER_elbow_R",
    "wrist_R": "V50_RIG_MARKER_wrist_R",
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-stride", type=int, default=8)
    parser.add_argument("--growth-ratio", type=float, default=0.035)
    # rest-ratio tightened 0.12 -> 0.06 (INC-140/T046): 0.12*height (~0.33) let a
    # visibly detached shoulder pass. See trouble_history [T046].
    parser.add_argument("--rest-ratio", type=float, default=0.06)
    # attach-ratio: direct parent<->child mesh proximity at rest. Marker-to-side
    # distances are blind to a marker parked in the gap; this measures whether the
    # two segments' meshes actually meet near the joint (T035 contact-patch lesson).
    # Calibrated 0.05 -> 0.06 against the accepted KEEP_ORIGINAL V50 layout: its own
    # wrist_R gap is 0.115 (0.0593*h). Pre-fix detached shoulders (0.27-0.28) still
    # fail at this tolerance by a 2.3x margin.
    parser.add_argument("--attach-ratio", type=float, default=0.06)
    parser.add_argument("--max-verts", type=int, default=1200)
    return parser.parse_args(argv)


def objects(names):
    return [bpy.data.objects[name] for name in names if name in bpy.data.objects and bpy.data.objects[name].type == "MESH"]


def all_robot_meshes():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name != "Ground"]


def bounds_for(objs):
    pts = []
    for obj in objs:
        pts.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def center_of(names):
    objs = objects(names)
    lo, hi = bounds_for(objs)
    return (lo + hi) * 0.5


def joint_specs():
    y = center_of(TORSO).y
    return [
        {"name": "shoulder_L", "parent": TORSO, "child": UPPER_ARM_L, "point": MARKERS["shoulder_L"]},
        {"name": "elbow_L", "parent": UPPER_ARM_L, "child": LOWER_ARM_L, "point": MARKERS["elbow_L"]},
        {"name": "wrist_L", "parent": LOWER_ARM_L, "child": HAND_L, "point": MARKERS["wrist_L"], "allow_missing_child": False},
        {"name": "shoulder_R", "parent": TORSO, "child": UPPER_ARM_R, "point": MARKERS["shoulder_R"]},
        {"name": "elbow_R", "parent": UPPER_ARM_R, "child": LOWER_ARM_R, "point": MARKERS["elbow_R"]},
        {"name": "wrist_R", "parent": LOWER_ARM_R, "child": HAND_R, "point": MARKERS["wrist_R"]},
        {"name": "hip_L", "parent": TORSO, "child": UPPER_LEG_L, "point": (-0.20, y, 0.02)},
        {"name": "knee_L", "parent": UPPER_LEG_L, "child": LOWER_LEG_L, "point": (-0.24, y, -0.50)},
        {"name": "ankle_L", "parent": LOWER_LEG_L, "child": FOOT_L, "point": (-0.25, y, -0.88)},
        {"name": "hip_R", "parent": TORSO, "child": UPPER_LEG_R, "point": (0.22, y, 0.02)},
        {"name": "knee_R", "parent": UPPER_LEG_R, "child": LOWER_LEG_R, "point": (0.25, y, -0.50)},
        {"name": "ankle_R", "parent": LOWER_LEG_R, "child": FOOT_R, "point": (0.26, y, -0.88)},
    ]


def resolve_point(point):
    if isinstance(point, str):
        obj = bpy.data.objects.get(point)
        if obj is None:
            raise RuntimeError(f"joint marker missing: {point}")
        if point.startswith("V50_RIG_MARKER_") and obj.parent is None:
            loc = obj.location.copy()
            if loc.length > 1.0e-6:
                return loc
        return obj.matrix_world.translation.copy()
    return Vector(point)


def sampled_world_vertices(obj, max_verts):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        count = len(mesh.vertices)
        if count <= 0:
            return []
        step = max(1, count // max_verts)
        mw = evaluated.matrix_world
        return [mw @ mesh.vertices[i].co for i in range(0, count, step)]
    finally:
        evaluated.to_mesh_clear()


def min_distance(point, objs, max_verts):
    best = None
    for obj in objs:
        for vertex in sampled_world_vertices(obj, max_verts):
            dist = (vertex - point).length
            if best is None or dist < best:
                best = dist
    return best


def min_pair_distance(parent_objs, child_objs, point, radius, max_verts):
    """Smallest distance between any parent vertex and any child vertex, restricted
    to vertices within `radius` of the joint `point`. Marker-independent: directly
    measures whether the two segments meet near the joint (INC-140/T046)."""
    def near_verts(objs):
        out = []
        for obj in objs:
            for v in sampled_world_vertices(obj, max_verts):
                if (v - point).length <= radius:
                    out.append(v)
        return out
    pv = near_verts(parent_objs)
    cv = near_verts(child_objs)
    if not pv or not cv:
        return None  # nothing near the joint on one side -> cannot confirm contact
    best = None
    for p in pv:
        for c in cv:
            d = (p - c).length
            if best is None or d < best:
                best = d
    return best


def frame_range(stride):
    start = int(bpy.context.scene.frame_start)
    end = int(bpy.context.scene.frame_end)
    frames = list(range(start, end + 1, max(1, stride)))
    if end not in frames:
        frames.append(end)
    return frames


def check_joint(spec, frames, max_verts, attach_radius):
    parent_objs = objects(spec["parent"])
    child_objs = objects(spec["child"])
    if not parent_objs or not child_objs:
        return {
            "joint": spec["name"],
            "pass": False,
            "reason": "parent_or_child_mesh_missing",
            "parent_object_count": len(parent_objs),
            "child_object_count": len(child_objs),
        }

    rows = []
    rest_pair_distance = None
    for idx, frame in enumerate(frames):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        point = resolve_point(spec["point"])
        parent_dist = min_distance(point, parent_objs, max_verts)
        child_dist = min_distance(point, child_objs, max_verts)
        if idx == 0:
            rest_pair_distance = min_pair_distance(
                parent_objs, child_objs, point, attach_radius, max_verts
            )
        rows.append({
            "frame": frame,
            "parent_distance": float(parent_dist) if parent_dist is not None else None,
            "child_distance": float(child_dist) if child_dist is not None else None,
        })
    rest = rows[0]
    max_parent = max(row["parent_distance"] for row in rows if row["parent_distance"] is not None)
    max_child = max(row["child_distance"] for row in rows if row["child_distance"] is not None)
    return {
        "joint": spec["name"],
        "parent_object_count": len(parent_objs),
        "child_object_count": len(child_objs),
        "rest_parent_distance": rest["parent_distance"],
        "rest_child_distance": rest["child_distance"],
        "max_parent_distance": max_parent,
        "max_child_distance": max_child,
        "parent_growth": max_parent - rest["parent_distance"],
        "child_growth": max_child - rest["child_distance"],
        "rest_pair_distance": float(rest_pair_distance) if rest_pair_distance is not None else None,
        "worst_parent_frame": max(rows, key=lambda row: row["parent_distance"] or -1)["frame"],
        "worst_child_frame": max(rows, key=lambda row: row["child_distance"] or -1)["frame"],
        "samples": rows,
    }


def unhide_measured_objects():
    """INC-140: viewport-hidden objects are excluded from depsgraph evaluation, so
    their matrix_world stays identity and sampled vertices are measured at the
    origin (seen as a bogus 1.38 wrist_L child distance). Un-hide every mesh for
    measurement; this gate never renders, so visibility side effects don't matter."""
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = False
            obj.hide_viewport = False
            try:
                obj.hide_set(False)
            except RuntimeError:
                pass  # not in current view layer
    bpy.context.view_layer.update()


def main():
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend)))
    unhide_measured_objects()
    meshes = all_robot_meshes()
    lo, hi = bounds_for(meshes)
    model_height = float((hi - lo).z)
    growth_tol = model_height * args.growth_ratio
    rest_tol = model_height * args.rest_ratio
    attach_tol = model_height * args.attach_ratio
    attach_radius = model_height * 0.30  # neighborhood around the joint to look for contact
    frames = frame_range(args.sample_stride)

    checks = []
    for spec in joint_specs():
        check = check_joint(spec, frames, args.max_verts, attach_radius)
        if "reason" not in check:
            fail_reasons = []
            if check["rest_parent_distance"] > rest_tol:
                fail_reasons.append("parent_far_from_joint_at_rest")
            if check["rest_child_distance"] > rest_tol:
                fail_reasons.append("child_far_from_joint_at_rest")
            if check["parent_growth"] > growth_tol:
                fail_reasons.append("parent_joint_gap_growth")
            if check["child_growth"] > growth_tol:
                fail_reasons.append("child_joint_gap_growth")
            # Direct parent<->child attachment test (marker-independent). None means
            # one side has no mesh near the joint -> also a detachment signal.
            rpd = check.get("rest_pair_distance")
            if rpd is None:
                fail_reasons.append("no_parent_child_contact_near_joint")
            elif rpd > attach_tol:
                fail_reasons.append("parent_child_meshes_detached_at_rest")
            check["pass"] = not fail_reasons
            check["fail_reasons"] = fail_reasons
        checks.append(check)

    failed = [row for row in checks if not row.get("pass")]
    report = {
        "schema": "clawstack.v50_joint_attachment_gate.v1",
        "source_blend": str(Path(args.blend)),
        "frames_sampled": frames,
        "model_height": round(model_height, 6),
        "growth_tol": round(growth_tol, 6),
        "rest_tol": round(rest_tol, 6),
        "attach_tol": round(attach_tol, 6),
        "verdict": "PASS_JOINT_ATTACHMENT" if not failed else "HOLD_JOINT_DETACHMENT",
        "telegram_allowed": not failed,
        "checks": checks,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "failed_joints": [row["joint"] for row in failed],
        "out": str(out),
    }, ensure_ascii=False), flush=True)
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
