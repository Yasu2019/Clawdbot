# -*- coding: utf-8 -*-
"""リグ付きメカFBXへモーションFBXを移植し、連番PNGとmp4を作る。

  python scripts/render_mecha_walk.py \
      --model "D:/Clawdbot_Docker_20260125/Gundam/FLB/Zaku_Rig_mixamo.fbx" \
      --motion "C:/Users/yasu/Downloads/Normal_Walking_RickDias.fbx" \
      --out workspace/sample_mecha_movie/output/zaku_walk \
      --views side,front,three_quarter --fps 24 --loops 3
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mecha_studio.adapters import blender, ffmpeg  # noqa: E402


def encode(frames_dir: Path, out_mp4: Path, fps: float, loops: int):
    """連番PNG -> mp4。歩行1サイクルは短いのでloops回だけ繰り返す。"""
    exe = ffmpeg.available()
    if not exe:
        print("ffmpeg が見つからないため mp4 化はスキップします")
        return None
    frames = sorted(frames_dir.glob("*.png"))
    if not frames:
        return None
    listfile = frames_dir / "_frames.txt"
    with listfile.open("w", encoding="utf-8") as f:
        for _ in range(max(1, loops)):
            for p in frames:
                f.write(f"file '{p.name}'\n")
                f.write(f"duration {1.0 / fps:.6f}\n")
        f.write(f"file '{frames[-1].name}'\n")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    # -r と -vsync vfr は併用不可（ffmpegが contradictory で落ちる）。CFRで固定する。
    cmd = [exe, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listfile),
           "-fps_mode", "cfr", "-r", str(fps),
           "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "18", str(out_mp4)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])
    return out_mp4


def main(argv=None):
    ap = argparse.ArgumentParser(description="リグ付きメカにモーションを移植してレンダする")
    ap.add_argument("--model", required=True, help="リグ付きメカFBX")
    ap.add_argument("--motion", required=True, help="モーション供給元FBX（同系リグ）")
    ap.add_argument("--out", required=True, help="出力ディレクトリ")
    ap.add_argument("--views", default="side", help="front,side,back,three_quarter のカンマ区切り")
    ap.add_argument("--step", type=int, default=1, help="フレーム間引き（1=全フレーム）")
    ap.add_argument("--resolution", type=int, default=640)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--loops", type=int, default=3, help="歩行サイクルの繰り返し回数")
    a = ap.parse_args(argv)

    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out

    print(f"blender: {blender.available()}")
    produced = blender.render_walk_animation(
        Path(a.model), Path(a.motion), out,
        views=a.views, step=a.step, resolution=a.resolution,
    )
    print(f"レンダ完了: {len(produced)} 枚")

    for view in [v.strip() for v in a.views.split(",") if v.strip()]:
        d = out / view
        mp4 = encode(d, out / f"{view}.mp4", a.fps, a.loops)
        if mp4:
            print(f"  {view}: {mp4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
