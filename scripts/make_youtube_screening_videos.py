#!/usr/bin/env python3
"""Package the validated virtual fields as annotated YouTube MP4 videos."""
from __future__ import annotations
import argparse, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = [
    ("fill", ROOT / "artifacts/box_roundhole_v5/box100x60x50_youtube_top_oblique_fill_v4_slow3x.mp4", 1.0,
     "Resin fill | alpha blue=unfilled, red=filled | virtual screening only"),
    ("warpage", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260909_r7/phenomenon_videos/box100x60x50_warpage_deformation_50x.mp4", 3.0,
     "Warpage 50x | contour blue=low, red=high | relative proxy, not mm"),
    ("sink", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260909_r7/phenomenon_videos/box100x60x50_sink_deformation_50x.mp4", 3.0,
     "Sink 50x | contour blue=low, red=high | relative proxy, not depth"),
    ("shrink", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260909_r7/phenomenon_videos/box100x60x50_shrink_deformation_50x.mp4", 3.0,
     "Shrinkage 50x | contour blue=low, red=high | virtual strain proxy"),
    ("weld", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260910_r15_geometry_void/box100x60x50_weld_virtual_animation.mp4", 3.0,
     "Weld-line candidate | contour blue=low, red=high | not weld strength"),
    ("airtrap", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260910_r15_geometry_void/box100x60x50_airtrap_virtual_animation.mp4", 3.0,
     "Air-trap candidate | contour blue=low, red=high | not trapped-air pressure"),
    ("void", ROOT / "artifacts/box_roundhole_v5/virtual_e2e_20260910_r15_geometry_void/box100x60x50_void_virtual_animation.mp4", 3.0,
     "Void candidate | contour blue=low, red=high | not CT-validated void fraction"),
]

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    for key, src, slow, caption in ITEMS:
        if not src.exists(): raise SystemExit(f"missing input: {src}")
        # Stretch the short phenomenon clips so their motion is inspectable;
        # fill is already the 10.1 s slow-playback version.
        vf = ["scale=1920:1080:force_original_aspect_ratio=decrease",
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"]
        if slow != 1.0: vf.append(f"setpts={slow:g}*PTS")
        vf += ["tpad=stop_mode=clone:stop_duration=1",
               "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='Contour interpretation - blue=low / red=high':x=40:y=30:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.55",
               f"drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='{caption}':x=40:y=70:fontsize=25:fontcolor=white:box=1:boxcolor=black@0.55",
               "format=yuv420p"]
        out = args.out_dir / f"box100x60x50_youtube_{key}_annotated.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", ",".join(vf),
               "-r", "30", "-t", "10", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
        print(out)
    return 0
if __name__ == "__main__": raise SystemExit(main())
