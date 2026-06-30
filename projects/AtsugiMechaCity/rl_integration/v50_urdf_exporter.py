"""
v50_urdf_exporter.py — V50 mecha URDF exporter

Extracts joint topology and positions from the V50 mecha's hardcoded pivot coordinates
(v50_final_walk_preview.py) and arm marker positions (v50_armature_build_report.json),
then writes a URDF file suitable for MuJoCo / Isaac Lab / DiffMimic.

Usage:
    python v50_urdf_exporter.py --out v50_mecha.urdf
    python v50_urdf_exporter.py --out v50_mecha.urdf --mass 280.0 --height 1.94
"""

import argparse
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ── Joint world-space positions (Blender XZ, Y depth collapsed to 0) ─────────
# Leg pivots from v50_final_walk_preview.py (authoritative)
# Arm pivots derived from *_SHARED_CORE objects in armature_build_report.json
# Shoulder estimated from bone midpoint targets in arm_segment_snap data

JOINTS_WORLD = {
    # torso root (centre of Torso_Core + Pelvis_Center, z averaged)
    "torso":       ( 0.013,  0.000,  0.354),
    # legs
    "hip_L":       (-0.200,  0.000,  0.020),
    "knee_L":      (-0.240,  0.000, -0.500),
    "ankle_L":     (-0.250,  0.000, -0.880),
    "hip_R":       ( 0.220,  0.000,  0.020),
    "knee_R":      ( 0.250,  0.000, -0.500),
    "ankle_R":     ( 0.260,  0.000, -0.880),
    # arms  (SHARED_CORE positions from armature_build_report.json)
    "shoulder_L":  (-0.518,  0.000,  0.541),   # 2*UpperArm_L_midpoint - elbow_L
    "elbow_L":     (-0.438,  0.000,  0.205),
    "wrist_L":     (-0.460,  0.000, -0.165),
    "shoulder_R":  ( 0.503,  0.000,  0.532),
    "elbow_R":     ( 0.455,  0.000,  0.190),
    "wrist_R":     ( 0.480,  0.000, -0.135),
}

# Joint types from v50_armature_build_report.json constraints field
# UpperArm = ball (3-DOF), LowerArm/Hand = hinge (1-DOF)
JOINT_CONFIG = {
    "hip_L":      {"type": "revolute", "axis": "1 0 0", "lower": -0.698, "upper":  0.698},
    "knee_L":     {"type": "revolute", "axis": "1 0 0", "lower": -0.524, "upper":  0.175},
    "ankle_L":    {"type": "revolute", "axis": "1 0 0", "lower": -0.349, "upper":  0.349},
    "hip_R":      {"type": "revolute", "axis": "1 0 0", "lower": -0.698, "upper":  0.698},
    "knee_R":     {"type": "revolute", "axis": "1 0 0", "lower": -0.524, "upper":  0.175},
    "ankle_R":    {"type": "revolute", "axis": "1 0 0", "lower": -0.349, "upper":  0.349},
    "shoulder_L": {"type": "revolute", "axis": "1 0 0", "lower": -1.745, "upper":  1.745},
    "elbow_L":    {"type": "revolute", "axis": "1 0 0", "lower": -2.094, "upper":  0.175},
    "wrist_L":    {"type": "revolute", "axis": "1 0 0", "lower": -0.524, "upper":  0.524},
    "shoulder_R": {"type": "revolute", "axis": "1 0 0", "lower": -1.745, "upper":  1.745},
    "elbow_R":    {"type": "revolute", "axis": "1 0 0", "lower": -2.094, "upper":  0.175},
    "wrist_R":    {"type": "revolute", "axis": "1 0 0", "lower": -0.524, "upper":  0.524},
}


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def length(v):
    return math.sqrt(sum(x * x for x in v))


def fmt3(v):
    return f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}"


def link_inertial(mass, ixx, iyy, izz):
    inertial = ET.Element("inertial")
    ET.SubElement(inertial, "mass", value=str(mass))
    ET.SubElement(inertial, "inertia",
                  ixx=str(ixx), ixy="0", ixz="0",
                  iyy=str(iyy), iyz="0", izz=str(izz))
    return inertial


def add_link(root_el, name, mass, radius=0.05, length_m=0.3):
    link = ET.SubElement(root_el, "link", name=name)
    link.append(link_inertial(
        mass,
        ixx=round(mass * (3 * radius ** 2 + length_m ** 2) / 12, 6),
        iyy=round(mass * (3 * radius ** 2 + length_m ** 2) / 12, 6),
        izz=round(mass * radius ** 2 / 2, 6),
    ))
    visual = ET.SubElement(link, "visual")
    geom = ET.SubElement(visual, "geometry")
    ET.SubElement(geom, "cylinder", radius=str(radius), length=str(length_m))
    return link


def add_joint(root_el, name, parent, child, origin_xyz, jtype, axis, lower, upper):
    jnt = ET.SubElement(root_el, "joint", name=name, type=jtype)
    ET.SubElement(jnt, "parent", link=parent)
    ET.SubElement(jnt, "child", link=child)
    ET.SubElement(jnt, "origin", xyz=fmt3(origin_xyz), rpy="0 0 0")
    ET.SubElement(jnt, "axis", xyz=axis)
    ET.SubElement(jnt, "limit",
                  lower=str(round(lower, 4)), upper=str(round(upper, 4)),
                  effort="500", velocity="3.14")
    return jnt


def build_urdf(total_mass: float = 280.0) -> ET.Element:
    J = JOINTS_WORLD

    # Segment lengths (used for inertia / geometry)
    seg_len = {
        "upper_leg":  length(sub(J["knee_L"], J["hip_L"])),
        "lower_leg":  length(sub(J["ankle_L"], J["knee_L"])),
        "upper_arm":  length(sub(J["elbow_L"], J["shoulder_L"])),
        "lower_arm":  length(sub(J["wrist_L"], J["elbow_L"])),
    }

    # Mass distribution (rough, total sums to total_mass)
    m = {
        "torso":     total_mass * 0.40,
        "upper_leg": total_mass * 0.08,   # × 2 sides
        "lower_leg": total_mass * 0.05,
        "foot":      total_mass * 0.02,
        "upper_arm": total_mass * 0.04,
        "lower_arm": total_mass * 0.025,
        "hand":      total_mass * 0.01,
    }

    robot = ET.Element("robot", name="V50_Mecha")

    # ── Links ─────────────────────────────────────────────────────────────────
    add_link(robot, "torso",      m["torso"],     radius=0.18, length_m=0.60)
    for side in ("L", "R"):
        add_link(robot, f"upper_leg_{side}", m["upper_leg"], radius=0.055, length_m=seg_len["upper_leg"])
        add_link(robot, f"lower_leg_{side}", m["lower_leg"], radius=0.045, length_m=seg_len["lower_leg"])
        add_link(robot, f"foot_{side}",      m["foot"],      radius=0.04,  length_m=0.18)
        add_link(robot, f"upper_arm_{side}", m["upper_arm"], radius=0.045, length_m=seg_len["upper_arm"])
        add_link(robot, f"lower_arm_{side}", m["lower_arm"], radius=0.035, length_m=seg_len["lower_arm"])
        add_link(robot, f"hand_{side}",      m["hand"],      radius=0.03,  length_m=0.12)

    # ── Joints ────────────────────────────────────────────────────────────────
    for side in ("L", "R"):
        s = side
        cfg = JOINT_CONFIG

        # Hip: torso → upper_leg
        hip_origin = sub(J[f"hip_{s}"], J["torso"])
        add_joint(robot, f"hip_{s}", "torso", f"upper_leg_{s}",
                  hip_origin, cfg[f"hip_{s}"]["type"],
                  cfg[f"hip_{s}"]["axis"],
                  cfg[f"hip_{s}"]["lower"], cfg[f"hip_{s}"]["upper"])

        # Knee: upper_leg → lower_leg
        knee_origin = sub(J[f"knee_{s}"], J[f"hip_{s}"])
        add_joint(robot, f"knee_{s}", f"upper_leg_{s}", f"lower_leg_{s}",
                  knee_origin, cfg[f"knee_{s}"]["type"],
                  cfg[f"knee_{s}"]["axis"],
                  cfg[f"knee_{s}"]["lower"], cfg[f"knee_{s}"]["upper"])

        # Ankle: lower_leg → foot
        ankle_origin = sub(J[f"ankle_{s}"], J[f"knee_{s}"])
        add_joint(robot, f"ankle_{s}", f"lower_leg_{s}", f"foot_{s}",
                  ankle_origin, cfg[f"ankle_{s}"]["type"],
                  cfg[f"ankle_{s}"]["axis"],
                  cfg[f"ankle_{s}"]["lower"], cfg[f"ankle_{s}"]["upper"])

        # Shoulder: torso → upper_arm
        sh_origin = sub(J[f"shoulder_{s}"], J["torso"])
        add_joint(robot, f"shoulder_{s}", "torso", f"upper_arm_{s}",
                  sh_origin, cfg[f"shoulder_{s}"]["type"],
                  cfg[f"shoulder_{s}"]["axis"],
                  cfg[f"shoulder_{s}"]["lower"], cfg[f"shoulder_{s}"]["upper"])

        # Elbow: upper_arm → lower_arm
        el_origin = sub(J[f"elbow_{s}"], J[f"shoulder_{s}"])
        add_joint(robot, f"elbow_{s}", f"upper_arm_{s}", f"lower_arm_{s}",
                  el_origin, cfg[f"elbow_{s}"]["type"],
                  cfg[f"elbow_{s}"]["axis"],
                  cfg[f"elbow_{s}"]["lower"], cfg[f"elbow_{s}"]["upper"])

        # Wrist: lower_arm → hand
        wr_origin = sub(J[f"wrist_{s}"], J[f"elbow_{s}"])
        add_joint(robot, f"wrist_{s}", f"lower_arm_{s}", f"hand_{s}",
                  wr_origin, cfg[f"wrist_{s}"]["type"],
                  cfg[f"wrist_{s}"]["axis"],
                  cfg[f"wrist_{s}"]["lower"], cfg[f"wrist_{s}"]["upper"])

    return robot


def prettify(element: ET.Element) -> str:
    raw = ET.tostring(element, encoding="unicode")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ")


def main():
    parser = argparse.ArgumentParser(description="Export V50 mecha URDF")
    parser.add_argument("--out", default="v50_mecha.urdf", help="Output URDF path")
    parser.add_argument("--mass", type=float, default=280.0, help="Total mass in kg")
    args = parser.parse_args()

    robot = build_urdf(total_mass=args.mass)
    xml_str = prettify(robot)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(f"Wrote {args.out}")

    # Print summary
    links  = [e.get("name") for e in robot.findall("link")]
    joints = [e.get("name") for e in robot.findall("joint")]
    print(f"  Links:  {len(links)}  -- {links}")
    print(f"  Joints: {len(joints)} -- {joints}")


if __name__ == "__main__":
    main()
