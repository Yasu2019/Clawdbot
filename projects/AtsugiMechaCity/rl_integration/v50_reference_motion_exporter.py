"""
v50_reference_motion_exporter.py — Export V50 sin-wave walk as RL reference motion

Replicates the exact animation math from v50_final_walk_preview.py (no Blender needed)
and writes:
  - v50_ref_motion.json  : AMP/Isaac Lab compatible reference motion format
  - v50_ref_motion.bvh   : BVH skeleton file for DiffMimic / Cascadeur import

Joint order (12 DOF + root):
  root_x, root_y, root_z,                (world root translation — V50 walks in place)
  root_rx, root_ry, root_rz,             (torso euler: bob → rz sway)
  hip_L, knee_L, ankle_L,
  hip_R, knee_R, ankle_R,
  shoulder_L, elbow_L, wrist_L,
  shoulder_R, elbow_R, wrist_R

Usage:
    python v50_reference_motion_exporter.py --frames 96 --fps 24
    python v50_reference_motion_exporter.py --frames 192 --fps 24 --cycles 4
"""

import argparse
import json
import math
from pathlib import Path


# ── Joint angle ranges from animation (peak values in degrees) ───────────────
# Source: v50_final_walk_preview.py  pose_armature() and animate()
#   swing_l = 7.0 * sin(cycle)    → hip flex/extend
#   knee_l  = 6.0 * max(0, -sin)  → knee flex only
#   foot_l  = -3.0 * max(0, -sin) → ankle plantarflex
#   UpperArm: -10 ± 12°           → shoulder, opposite phase to leg
#   LowerArm: -18 - 18*bend       → elbow
#   Hand:     -8 - 8*bend         → wrist


def compute_frame(frame: int, total_frames: int, n_cycles: int = 2) -> dict:
    phase = (frame - 1) / max(total_frames - 1, 1)
    cycle = phase * math.tau * n_cycles

    swing = math.sin(cycle)
    bend_l = (math.sin(cycle - math.pi / 3.0) + 1.0) * 0.5
    bend_r = 1.0 - bend_l

    # Torso
    bob = 0.025 * (0.5 - 0.5 * math.cos(phase * math.tau * 4.0))
    sway = math.radians(1.2) * math.sin(cycle)

    # Leg joints (radians, positive = forward flex)
    hip_L   =  math.radians(7.0 * math.sin(cycle))
    knee_L  =  math.radians(6.0 * max(0.0, -math.sin(cycle)))
    ankle_L =  math.radians(-3.0 * max(0.0, -math.sin(cycle)))
    hip_R   =  math.radians(-7.0 * math.sin(cycle))
    knee_R  =  math.radians(6.0 * max(0.0, math.sin(cycle)))
    ankle_R =  math.radians(-3.0 * max(0.0, math.sin(cycle)))

    # Arm joints (radians, negative = flex forward / down in Blender convention)
    sh_L   = math.radians(-10.0 + 12.0 * swing)
    el_L   = math.radians(-18.0 - 18.0 * bend_l)
    wr_L   = math.radians(-8.0 - 8.0 * bend_l)
    sh_R   = math.radians(-10.0 - 12.0 * swing)
    el_R   = math.radians(-18.0 - 18.0 * bend_r)
    wr_R   = math.radians(-8.0 - 8.0 * bend_r)

    return {
        "root_z":    bob,
        "root_rz":   sway,
        "hip_L":     hip_L,
        "knee_L":    knee_L,
        "ankle_L":   ankle_L,
        "hip_R":     hip_R,
        "knee_R":    knee_R,
        "ankle_R":   ankle_R,
        "shoulder_L": sh_L,
        "elbow_L":   el_L,
        "wrist_L":   wr_L,
        "shoulder_R": sh_R,
        "elbow_R":   el_R,
        "wrist_R":   wr_R,
    }


# ── AMP / Isaac Lab format ────────────────────────────────────────────────────
# Each row: [dt, root_x, root_y, root_z, root_rx, root_ry, root_rz, <12 joints>]
def export_amp_json(frames: int, fps: int, cycles: int, out_path: Path) -> None:
    dt = 1.0 / fps
    rows = []
    for f in range(1, frames + 1):
        d = compute_frame(f, frames, cycles)
        row = [
            round(dt, 6),
            0.0, 0.0, round(d["root_z"], 6),   # root pos (walk in place)
            0.0, 0.0, round(d["root_rz"], 6),   # root rot euler
            round(d["hip_L"],     6),
            round(d["knee_L"],    6),
            round(d["ankle_L"],   6),
            round(d["hip_R"],     6),
            round(d["knee_R"],    6),
            round(d["ankle_R"],   6),
            round(d["shoulder_L"], 6),
            round(d["elbow_L"],   6),
            round(d["wrist_L"],   6),
            round(d["shoulder_R"], 6),
            round(d["elbow_R"],   6),
            round(d["wrist_R"],   6),
        ]
        rows.append(row)

    payload = {
        "schema": "clawstack.v50_reference_motion.amp.v1",
        "Loop": "wrap",
        "FrameDuration": dt,
        "TotalFrames": frames,
        "Cycles": cycles,
        "DOFOrder": [
            "root_x", "root_y", "root_z",
            "root_rx", "root_ry", "root_rz",
            "hip_L", "knee_L", "ankle_L",
            "hip_R", "knee_R", "ankle_R",
            "shoulder_L", "elbow_L", "wrist_L",
            "shoulder_R", "elbow_R", "wrist_R",
        ],
        "Frames": rows,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"AMP JSON → {out_path}  ({frames} frames, {cycles} cycles)")


# ── BVH export ────────────────────────────────────────────────────────────────
# Minimal BVH suitable for DiffMimic / Cascadeur / Auto-Rig Pro retargeting
BVH_SKELETON = """\
HIERARCHY
ROOT Hips
{{
    OFFSET 0.00 88.00 0.00
    CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
    JOINT UpperLeg_L
    {{
        OFFSET -20.00 -33.40 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT LowerLeg_L
        {{
            OFFSET -4.00 -52.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            JOINT Foot_L
            {{
                OFFSET -1.00 -38.00 0.00
                CHANNELS 3 Zrotation Xrotation Yrotation
                End Site
                {{
                    OFFSET 0.00 -15.00 0.00
                }}
            }}
        }}
    }}
    JOINT UpperLeg_R
    {{
        OFFSET 20.70 -33.40 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT LowerLeg_R
        {{
            OFFSET 3.00 -52.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            JOINT Foot_R
            {{
                OFFSET 1.00 -38.00 0.00
                CHANNELS 3 Zrotation Xrotation Yrotation
                End Site
                {{
                    OFFSET 0.00 -15.00 0.00
                }}
            }}
        }}
    }}
    JOINT Chest
    {{
        OFFSET 0.00 18.70 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT UpperArm_L
        {{
            OFFSET -53.10 0.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            JOINT LowerArm_L
            {{
                OFFSET 8.00 -33.60 0.00
                CHANNELS 3 Zrotation Xrotation Yrotation
                JOINT Hand_L
                {{
                    OFFSET -2.20 -37.00 0.00
                    CHANNELS 3 Zrotation Xrotation Yrotation
                    End Site
                    {{
                        OFFSET 0.00 -12.00 0.00
                    }}
                }}
            }}
        }}
        JOINT UpperArm_R
        {{
            OFFSET 49.00 0.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            JOINT LowerArm_R
            {{
                OFFSET -4.80 -34.20 0.00
                CHANNELS 3 Zrotation Xrotation Yrotation
                JOINT Hand_R
                {{
                    OFFSET 2.50 -32.50 0.00
                    CHANNELS 3 Zrotation Xrotation Yrotation
                    End Site
                    {{
                        OFFSET 0.00 -12.00 0.00
                    }}
                }}
            }}
        }}
    }}
}}
"""


def export_bvh(frames: int, fps: int, cycles: int, out_path: Path) -> None:
    lines = [BVH_SKELETON]
    lines.append(f"MOTION\nFrames: {frames}\nFrame Time: {1.0/fps:.6f}\n")
    for f in range(1, frames + 1):
        d = compute_frame(f, frames, cycles)
        r2d = math.degrees

        # Root: Xpos Ypos Zpos Zrot Xrot Yrot (BVH Y-up)
        root_y = 88.0 + d["root_z"] * 100.0
        root_rz = r2d(d["root_rz"])

        parts = [
            f"0.000 {root_y:.4f} 0.000 {root_rz:.4f} 0.000 0.000",
            # UpperLeg_L (hip)
            f"0.000 {r2d(d['hip_L']):.4f} 0.000",
            # LowerLeg_L (knee)
            f"0.000 {r2d(d['knee_L']):.4f} 0.000",
            # Foot_L (ankle)
            f"0.000 {r2d(d['ankle_L']):.4f} 0.000",
            # UpperLeg_R (hip)
            f"0.000 {r2d(d['hip_R']):.4f} 0.000",
            # LowerLeg_R (knee)
            f"0.000 {r2d(d['knee_R']):.4f} 0.000",
            # Foot_R (ankle)
            f"0.000 {r2d(d['ankle_R']):.4f} 0.000",
            # Chest (torso sway carried here)
            f"{root_rz:.4f} 0.000 0.000",
            # UpperArm_L
            f"0.000 {r2d(d['shoulder_L']):.4f} 0.000",
            # LowerArm_L
            f"0.000 {r2d(d['elbow_L']):.4f} 0.000",
            # Hand_L
            f"0.000 {r2d(d['wrist_L']):.4f} 0.000",
            # UpperArm_R
            f"0.000 {r2d(d['shoulder_R']):.4f} 0.000",
            # LowerArm_R
            f"0.000 {r2d(d['elbow_R']):.4f} 0.000",
            # Hand_R
            f"0.000 {r2d(d['wrist_R']):.4f} 0.000",
        ]
        lines.append(" ".join(parts))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"BVH       → {out_path}  ({frames} frames, {cycles} cycles)")


def main():
    parser = argparse.ArgumentParser(description="Export V50 sin-wave walk as RL reference motion")
    parser.add_argument("--frames", type=int, default=96, help="Number of frames (default: 96 = 4s@24fps)")
    parser.add_argument("--fps",    type=int, default=24)
    parser.add_argument("--cycles", type=int, default=2,  help="Gait cycles in animation (default: 2)")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    export_amp_json(args.frames, args.fps, args.cycles, out / "v50_ref_motion.json")
    export_bvh(     args.frames, args.fps, args.cycles, out / "v50_ref_motion.bvh")


if __name__ == "__main__":
    main()
