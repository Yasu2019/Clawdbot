# -*- coding: utf-8 -*-
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from ..core.paths import ROOT


def available():
    return shutil.which("blender")


def render_reference_views(model_path: Path, output_dir: Path):
    exe = available()
    if not exe:
        raise RuntimeError("blender がPATHから見つかりません")
    script = ROOT / "mecha_studio" / "blender" / "render_reference_views.py"
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--background", "--python", str(script), "--", str(model_path), str(output_dir)]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-4000:])
    return str(output_dir)
