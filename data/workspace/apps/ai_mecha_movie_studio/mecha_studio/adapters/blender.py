# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess
from pathlib import Path
from ..core.paths import ROOT
from ..core.scanner import resolve_tool


def available():
    """PATHに無くても Program Files 等の既知インストール先から探す。"""
    return resolve_tool("blender")


def render_reference_views(model_path: Path, output_dir: Path):
    exe = available()
    if not exe:
        raise RuntimeError("blender が見つかりません（PATHにも既知インストール先にもありません）")
    script = ROOT / "mecha_studio" / "blender" / "render_reference_views.py"
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--background", "--python", str(script), "--", str(model_path), str(output_dir)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-4000:])
    return str(output_dir)
