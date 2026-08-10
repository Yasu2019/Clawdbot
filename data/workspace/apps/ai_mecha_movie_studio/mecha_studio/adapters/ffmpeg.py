# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess
from pathlib import Path
from ..core.scanner import resolve_tool


def available():
    return resolve_tool("ffmpeg")


def make_smoke_video(output: Path, seconds: int = 5):
    exe = available()
    if not exe:
        raise RuntimeError("ffmpeg が見つかりません")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe, "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(output),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])
    return str(output)
