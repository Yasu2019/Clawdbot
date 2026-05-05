"""Render CUT_009 from CUT_008 with Bulma moved toward the evidence board."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE = ROOT / "data/workspace/render_iatf_cut008_bulma_probe_once.py"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    replacements = {
        "CUT_008": "CUT_009",
        "CUT008": "CUT009",
        "cut008_bulma_probe": "cut009_bulma_probe",
        "iatf_cut008_bulma_probe": "iatf_cut009_bulma_probe",
        "cut008_bulma_": "cut009_bulma_",
        "larger Bulma only framing review": "Bulma closer to evidence board review",
        'bulma_arm, bulma_meshes = import_character(BULMA, "Bulma", (-1.95, -0.10, 0.0), fixed_scale=0.019, zrot=0.0)': 'bulma_arm, bulma_meshes = import_character(BULMA, "Bulma", (-1.58, -0.10, 0.0), fixed_scale=0.021, zrot=0.0)',
        'mouth = add_cube("bulma_mouth_overlay", (-1.95, -0.37, 0.28), (0.020, 0.010, 0.006), mouth_m)': 'mouth = add_cube("bulma_mouth_overlay", (-1.58, -0.37, 0.34), (0.024, 0.010, 0.006), mouth_m)',
        'left_lid = add_cube("bulma_left_blink_overlay", (-1.965, -0.38, 0.31), (0.014, 0.010, 0.004), lid_m)': 'left_lid = add_cube("bulma_left_blink_overlay", (-1.598, -0.38, 0.38), (0.016, 0.010, 0.004), lid_m)',
        'right_lid = add_cube("bulma_right_blink_overlay", (-1.935, -0.38, 0.31), (0.014, 0.010, 0.004), lid_m)': 'right_lid = add_cube("bulma_right_blink_overlay", (-1.562, -0.38, 0.38), (0.016, 0.010, 0.004), lid_m)',
        "camera.data.ortho_scale = 3.25": "camera.data.ortho_scale = 2.85",
        "IATF CUT008診断フレーム生成OKです。": "IATF CUT009診断フレーム生成OKです。",
        "IATF CUT008診断フレーム生成NGのため、次PDCAが必要です。": "IATF CUT009診断フレーム生成NGのため、次PDCAが必要です。",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    with tempfile.TemporaryDirectory(prefix="iatf_cut009_bulma_") as tmp:
        script = Path(tmp) / "render_cut009.py"
        script.write_text(text, encoding="utf-8")
        result = subprocess.run(
            ["python", str(script)],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
