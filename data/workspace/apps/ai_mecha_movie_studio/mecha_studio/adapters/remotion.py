# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess
from pathlib import Path
from ..core.scanner import resolve_tool


def available():
    return resolve_tool("npx")


def render(project_dir: Path, composition="Main", output="out/final.mp4"):
    npx = available()
    if not npx:
        raise RuntimeError("npx が見つかりません")
    cmd = [npx, "remotion", "render", composition, output]
    p = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-4000:])
    return str(project_dir / output)
