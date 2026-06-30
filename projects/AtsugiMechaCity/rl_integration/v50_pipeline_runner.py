"""
v50_pipeline_runner.py -- One-shot pipeline: generate all RL artifacts for V50

Runs in order:
  1. v50_urdf_exporter.py  → v50_mecha.urdf
  2. v50_mjcf_builder.py   → v50_mecha.xml
  3. v50_reference_motion_exporter.py → v50_ref_motion.json + v50_ref_motion.bvh
  4. Prints next-step instructions

Usage (no Blender needed -- pure Python 3.10+):
    python v50_pipeline_runner.py
    python v50_pipeline_runner.py --out-dir ./artifacts --mass 280
"""

import argparse
import subprocess
import sys
from pathlib import Path


STEPS = [
    {
        "name": "URDF export",
        "script": "v50_urdf_exporter.py",
        "extra_args": lambda args: ["--out", str(args.out_dir / "v50_mecha.urdf"),
                                    "--mass", str(args.mass)],
    },
    {
        "name": "MJCF build",
        "script": "v50_mjcf_builder.py",
        "extra_args": lambda args: ["--out", str(args.out_dir / "v50_mecha.xml"),
                                    "--mass", str(args.mass)],
    },
    {
        "name": "Reference motion export",
        "script": "v50_reference_motion_exporter.py",
        "extra_args": lambda args: ["--frames", str(args.frames),
                                    "--fps", str(args.fps),
                                    "--cycles", str(args.cycles),
                                    "--out-dir", str(args.out_dir)],
    },
]


def run_step(step: dict, args) -> bool:
    script = Path(__file__).parent / step["script"]
    cmd = [sys.executable, str(script)] + step["extra_args"](args)
    print(f"\n[{step['name']}] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"  ERROR: exit code {result.returncode}", file=sys.stderr)
        return False
    return True


def print_next_steps(out_dir: Path) -> None:
    print("\n" + "=" * 60)
    print("V50 RL artifact generation complete.")
    print("=" * 60)
    print(f"\nGenerated files in {out_dir}:")
    for f in sorted(out_dir.glob("v50_*")):
        print(f"  {f.name:40s} ({f.stat().st_size:,} bytes)")

    print("""
── Next steps ─────────────────────────────────────────────────

Option A: DiffMimic (fastest to working physics, no motion data needed)
  # Use existing Blender keyframes as reference
  git clone https://github.com/diffmimic/diffmimic
  cd diffmimic
  python train.py --mjcf v50_mecha.xml --ref_motion v50_ref_motion.json

Option B: Genesis RL (43M FPS on RTX 4090, Apache-2.0)
  pip install genesis-world
  # Write a Genesis env wrapping v50_mecha.xml + v50_amp_config.yaml
  # See: https://genesis-world.readthedocs.io

Option C: Isaac Lab AMP (NVIDIA, BSD-3, best multi-modal support)
  git clone https://github.com/isaac-sim/IsaacLab
  # Register V50 as a custom robot asset using v50_mecha.urdf
  # Use AmpHumanoid as template, swap in v50_ref_motion.json
  # See: IsaacLab/source/extensions/omni.isaac.lab_tasks/omni/isaac/lab_tasks/locomotion/velocity/mdp

Option D: PHC / PULSE (CMU, MIT, AMASS-trained -- best starting checkpoint)
  git clone https://github.com/ZhengyiLuo/PHC
  # PHC pre-trained on AMASS 40h+ -- load checkpoint and fine-tune on v50_ref_motion.json
  # Requires v50_mecha.xml with SMPL-compatible joint order

Style upgrade (after baseline works):
  1. Download 100STYLES: https://zenodo.org/record/6778383
     (CC BY 4.0, BVH, 4M+ frames, 100 walk styles)
  2. Retarget to V50 skeleton via Auto-Rig Pro or:
     python -c "import bpy; ..." (Auto-Rig Pro CLI retarget)
  3. Update reference_motion.path in v50_amp_config.yaml

Video → MoCap (optional, no dataset download needed):
  - DeepMotion Animate3D: upload mecha footage → BVH download
  - WHAM: https://github.com/yohanshin/WHAM (world-grounded, CVPR 2024)
  - MoCapAnything: arXiv 2512.10881 (supports non-humanoid rigs, watch for stable release)
""")


def main():
    parser = argparse.ArgumentParser(description="Run V50 RL pipeline (no Blender needed)")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "artifacts")
    parser.add_argument("--mass",   type=float, default=280.0)
    parser.add_argument("--frames", type=int,   default=96)
    parser.add_argument("--fps",    type=int,   default=24)
    parser.add_argument("--cycles", type=int,   default=2)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for step in STEPS:
        ok = run_step(step, args)
        if not ok:
            print(f"\nPipeline aborted at step: {step['name']}", file=sys.stderr)
            sys.exit(1)

    print_next_steps(args.out_dir)


if __name__ == "__main__":
    main()
