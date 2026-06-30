"""
v50_mjcf_builder.py — V50 mecha MuJoCo MJCF builder

Generates a MuJoCo MJCF XML for the V50 mecha skeleton, compatible with:
  - PHC / PULSE (CMU, MIT) — AMASS-trained physics controller
  - AMP / ASE (NVIDIA, BSD-3) — adversarial motion priors in Isaac Lab
  - DiffMimic (Apache-2.0) — differentiable imitation from keyframes
  - Genesis RL environment (Apache-2.0) — fastest sim (43M FPS on RTX 4090)

Joint positions derived from v50_urdf_exporter.py (same JOINTS_WORLD dict).

Usage:
    python v50_mjcf_builder.py --out v50_mecha.xml
    python v50_mjcf_builder.py --out v50_mecha.xml --mass 280 --floor
"""

import argparse
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ── Joint positions (world XZ, Y=0) — same as v50_urdf_exporter.py ─────────
JOINTS_WORLD = {
    "torso":      ( 0.013, 0.000,  0.354),
    "hip_L":      (-0.200, 0.000,  0.020),
    "knee_L":     (-0.240, 0.000, -0.500),
    "ankle_L":    (-0.250, 0.000, -0.880),
    "hip_R":      ( 0.220, 0.000,  0.020),
    "knee_R":     ( 0.250, 0.000, -0.500),
    "ankle_R":    ( 0.260, 0.000, -0.880),
    "shoulder_L": (-0.518, 0.000,  0.541),
    "elbow_L":    (-0.438, 0.000,  0.205),
    "wrist_L":    (-0.460, 0.000, -0.165),
    "shoulder_R": ( 0.503, 0.000,  0.532),
    "elbow_R":    ( 0.455, 0.000,  0.190),
    "wrist_R":    ( 0.480, 0.000, -0.135),
}

# Joint limits (radians) — conservative for RL stability
LIMITS = {
    "hip":      (-0.698,  0.698),   # ±40°
    "knee":     (-0.524,  0.175),   # -30° / +10° (knee bends backward)
    "ankle":    (-0.349,  0.349),   # ±20°
    "shoulder": (-1.745,  1.745),   # ±100°
    "elbow":    (-2.094,  0.175),   # -120° / +10°
    "wrist":    (-0.524,  0.524),   # ±30°
}


def sub(a, b):
    return tuple(round(a[i] - b[i], 6) for i in range(3))


def seg_len(j1, j2):
    d = sub(j2, j1)
    return round(math.sqrt(sum(x * x for x in d)), 4)


def f3(v):
    return f"{v[0]} {v[1]} {v[2]}"


def add_geom_capsule(parent, name, frompos, topos, radius=0.04):
    ET.SubElement(parent, "geom",
                  name=name, type="capsule",
                  fromto=f"{f3(frompos)} {f3(topos)}",
                  size=str(radius))


def add_body(parent, name, pos, mass, inertia_diag):
    body = ET.SubElement(parent, "body", name=name, pos=f3(pos))
    ET.SubElement(body, "inertial",
                  pos="0 0 0", mass=str(mass),
                  diaginertia=f"{inertia_diag[0]} {inertia_diag[1]} {inertia_diag[2]}")
    return body


def add_hinge(body, name, axis, lo, hi):
    ET.SubElement(body, "joint",
                  name=name, type="hinge",
                  axis=axis, pos="0 0 0",
                  limited="true",
                  range=f"{math.degrees(lo):.1f} {math.degrees(hi):.1f}",
                  damping="5", stiffness="0")


def build_mjcf(total_mass: float = 280.0, add_floor: bool = True) -> ET.Element:
    J = JOINTS_WORLD
    L = LIMITS

    # Mass per segment
    m = {
        "torso":     total_mass * 0.40,
        "upper_leg": total_mass * 0.08,
        "lower_leg": total_mass * 0.05,
        "foot":      total_mass * 0.02,
        "upper_arm": total_mass * 0.04,
        "lower_arm": total_mass * 0.025,
        "hand":      total_mass * 0.01,
    }

    mujoco = ET.Element("mujoco", model="V50_Mecha")

    # ── Compiler ─────────────────────────────────────────────────────────────
    ET.SubElement(mujoco, "compiler",
                  angle="degree", coordinate="local", inertiafromgeom="false")

    # ── Options ──────────────────────────────────────────────────────────────
    ET.SubElement(mujoco, "option",
                  timestep="0.002", integrator="RK4",
                  gravity="0 0 -9.81")

    # ── Default actuator/geom settings ───────────────────────────────────────
    default = ET.SubElement(mujoco, "default")
    ET.SubElement(default, "geom",
                  condim="3", friction="1.0 0.005 0.0001",
                  material="", contype="1", conaffinity="1")
    ET.SubElement(default, "motor", ctrllimited="true", ctrlrange="-1 1")

    # ── Assets ───────────────────────────────────────────────────────────────
    asset = ET.SubElement(mujoco, "asset")
    ET.SubElement(asset, "texture",
                  builtin="gradient", height="100", rgb1="0.3 0.35 0.4",
                  rgb2="0.0 0.0 0.0", type="skybox", width="100")
    ET.SubElement(asset, "texture",
                  builtin="flat", height="1278", mark="cross",
                  markrgb="1 1 1", name="texgeom",
                  random="0.01", rgb1="0.8 0.6 0.4", rgb2="0.8 0.6 0.4",
                  type="cube", width="127")
    ET.SubElement(asset, "material",
                  name="MatGeom", reflectance="0", shininess="0.1",
                  specular="0.5", texrepeat="5 5", texture="texgeom")

    # ── World body ───────────────────────────────────────────────────────────
    worldbody = ET.SubElement(mujoco, "worldbody")

    if add_floor:
        ET.SubElement(worldbody, "geom",
                      name="floor", pos="0 0 -0.92", size="20 20 0.1",
                      type="plane", material="MatGeom")

    ET.SubElement(worldbody, "light",
                  cutoff="100", diffuse="1 1 1", dir="-0 0 -1.3",
                  directional="true", exponent="1", pos="0 0 2.5",
                  specular="0.1 0.1 0.1")

    # ── Torso (root body, free joint for full locomotion) ────────────────────
    inertia_torso = (total_mass * 0.40 * 0.02, total_mass * 0.40 * 0.02, total_mass * 0.40 * 0.015)
    torso = add_body(worldbody, "torso",
                     pos=J["torso"],
                     mass=m["torso"],
                     inertia_diag=inertia_torso)
    ET.SubElement(torso, "joint",
                  name="root", type="free", pos="0 0 0", limited="false")
    # Torso capsule (head to pelvis)
    ET.SubElement(torso, "geom",
                  name="torso_geom", type="capsule",
                  fromto="0 0 0.30 0 0 -0.35", size="0.12", material="MatGeom")

    # ── Leg helper ───────────────────────────────────────────────────────────
    def add_leg(parent_body, side):
        s = side
        L_up   = seg_len(J[f"hip_{s}"],   J[f"knee_{s}"])
        L_lo   = seg_len(J[f"knee_{s}"],  J[f"ankle_{s}"])

        # Upper leg body (at hip, relative to torso)
        hip_rel = sub(J[f"hip_{s}"], J["torso"])
        uleg = add_body(parent_body, f"upper_leg_{s}",
                        pos=hip_rel,
                        mass=m["upper_leg"],
                        inertia_diag=(m["upper_leg"] * (L_up**2) / 12,) * 3)
        add_hinge(uleg, f"hip_{s}", "1 0 0", *L["hip"])
        # Geom along segment toward knee
        knee_rel = sub(J[f"knee_{s}"], J[f"hip_{s}"])
        ET.SubElement(uleg, "geom", name=f"upper_leg_{s}_geom",
                      type="capsule",
                      fromto=f"0 0 0 {f3(knee_rel)}",
                      size="0.045", material="MatGeom")

        # Lower leg body (at knee, relative to upper leg)
        lleg = add_body(uleg, f"lower_leg_{s}",
                        pos=knee_rel,
                        mass=m["lower_leg"],
                        inertia_diag=(m["lower_leg"] * (L_lo**2) / 12,) * 3)
        add_hinge(lleg, f"knee_{s}", "1 0 0", *L["knee"])
        ankle_rel = sub(J[f"ankle_{s}"], J[f"knee_{s}"])
        ET.SubElement(lleg, "geom", name=f"lower_leg_{s}_geom",
                      type="capsule",
                      fromto=f"0 0 0 {f3(ankle_rel)}",
                      size="0.038", material="MatGeom")

        # Foot body (at ankle, relative to lower leg)
        foot_end = (ankle_rel[0], ankle_rel[1], ankle_rel[2] - 0.05)
        foot = add_body(lleg, f"foot_{s}",
                        pos=ankle_rel,
                        mass=m["foot"],
                        inertia_diag=(m["foot"] * 0.003,) * 3)
        add_hinge(foot, f"ankle_{s}", "1 0 0", *L["ankle"])
        ET.SubElement(foot, "geom", name=f"foot_{s}_geom",
                      type="capsule",
                      fromto="0 0 0 0.15 0 -0.05",
                      size="0.032", material="MatGeom")
        # Contact sphere for ground contact
        ET.SubElement(foot, "geom", name=f"foot_{s}_contact",
                      type="sphere", size="0.04", pos="0.15 0 -0.08",
                      condim="6", friction="1.5 0.01 0.001")

    add_leg(torso, "L")
    add_leg(torso, "R")

    # ── Arm helper ───────────────────────────────────────────────────────────
    def add_arm(parent_body, side):
        s = side
        L_up = seg_len(J[f"shoulder_{s}"], J[f"elbow_{s}"])
        L_lo = seg_len(J[f"elbow_{s}"],   J[f"wrist_{s}"])

        sh_rel = sub(J[f"shoulder_{s}"], J["torso"])
        uarm = add_body(parent_body, f"upper_arm_{s}",
                        pos=sh_rel,
                        mass=m["upper_arm"],
                        inertia_diag=(m["upper_arm"] * (L_up**2) / 12,) * 3)
        add_hinge(uarm, f"shoulder_{s}", "1 0 0", *L["shoulder"])
        el_rel = sub(J[f"elbow_{s}"], J[f"shoulder_{s}"])
        ET.SubElement(uarm, "geom", name=f"upper_arm_{s}_geom",
                      type="capsule",
                      fromto=f"0 0 0 {f3(el_rel)}",
                      size="0.038", material="MatGeom")

        larm = add_body(uarm, f"lower_arm_{s}",
                        pos=el_rel,
                        mass=m["lower_arm"],
                        inertia_diag=(m["lower_arm"] * (L_lo**2) / 12,) * 3)
        add_hinge(larm, f"elbow_{s}", "1 0 0", *L["elbow"])
        wr_rel = sub(J[f"wrist_{s}"], J[f"elbow_{s}"])
        ET.SubElement(larm, "geom", name=f"lower_arm_{s}_geom",
                      type="capsule",
                      fromto=f"0 0 0 {f3(wr_rel)}",
                      size="0.030", material="MatGeom")

        hand = add_body(larm, f"hand_{s}",
                        pos=wr_rel,
                        mass=m["hand"],
                        inertia_diag=(m["hand"] * 0.001,) * 3)
        add_hinge(hand, f"wrist_{s}", "1 0 0", *L["wrist"])
        ET.SubElement(hand, "geom", name=f"hand_{s}_geom",
                      type="sphere", size="0.03", pos="0 0 -0.06",
                      material="MatGeom")

    add_arm(torso, "L")
    add_arm(torso, "R")

    # ── Actuators (one per DOF, torque-controlled) ───────────────────────────
    actuator = ET.SubElement(mujoco, "actuator")
    joint_names = [
        "hip_L", "knee_L", "ankle_L",
        "hip_R", "knee_R", "ankle_R",
        "shoulder_L", "elbow_L", "wrist_L",
        "shoulder_R", "elbow_R", "wrist_R",
    ]
    gear = {
        "hip": 400, "knee": 300, "ankle": 200,
        "shoulder": 200, "elbow": 150, "wrist": 80,
    }
    for jname in joint_names:
        jtype = jname.split("_")[0]
        ET.SubElement(actuator, "motor",
                      name=f"act_{jname}",
                      joint=jname,
                      gear=str(gear.get(jtype, 150)))

    # ── Sensors ──────────────────────────────────────────────────────────────
    sensor = ET.SubElement(mujoco, "sensor")
    for jname in joint_names:
        ET.SubElement(sensor, "jointpos",  name=f"pos_{jname}",  joint=jname)
        ET.SubElement(sensor, "jointvel",  name=f"vel_{jname}",  joint=jname)
    ET.SubElement(sensor, "accelerometer", name="torso_accel", site="torso_site" if False else "")
    sensor.remove(sensor[-1])  # remove placeholder accelerometer

    return mujoco


def prettify(element: ET.Element) -> str:
    raw = ET.tostring(element, encoding="unicode")
    from xml.dom import minidom
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="  ")


def main():
    parser = argparse.ArgumentParser(description="Build V50 mecha MuJoCo MJCF")
    parser.add_argument("--out",   default="v50_mecha.xml")
    parser.add_argument("--mass",  type=float, default=280.0)
    parser.add_argument("--floor", action="store_true", default=True)
    args = parser.parse_args()

    mujoco = build_mjcf(total_mass=args.mass, add_floor=args.floor)
    xml_str = prettify(mujoco)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(xml_str)
    print(f"Wrote {args.out}")

    bodies  = [e.get("name") for e in mujoco.iter("body")]
    joints  = [e.get("name") for e in mujoco.iter("joint") if e.get("name") != "root"]
    actuators = [e.get("name") for e in mujoco.iter("motor") if e.get("name")]
    print(f"  Bodies:    {len(bodies)}")
    print(f"  Joints:    {len(joints)} -- {joints}")
    print(f"  Actuators: {len(actuators)}")


if __name__ == "__main__":
    main()
