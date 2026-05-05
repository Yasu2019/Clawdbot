"""Render CUT_008 from CUT_007 with stronger visual QA framing."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE = ROOT / "data/workspace/render_iatf_cut007_bulma_probe_once.py"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    replacements = {
        "CUT_007": "CUT_008",
        "CUT007": "CUT008",
        "cut007_bulma_probe": "cut008_bulma_probe",
        "iatf_cut007_bulma_probe": "iatf_cut008_bulma_probe",
        "cut007_bulma_": "cut008_bulma_",
        "gentle coordinated arm motion review": "larger Bulma only framing review",
        'bulma_arm, bulma_meshes = import_character(BULMA, "Bulma", (-1.95, -0.10, 0.0), fixed_scale=0.015, zrot=0.0)': 'bulma_arm, bulma_meshes = import_character(BULMA, "Bulma", (-1.95, -0.10, 0.0), fixed_scale=0.019, zrot=0.0)',
        "for obj in goku_meshes:\n    obj.hide_render = False": "for obj in goku_meshes:\n    obj.hide_render = True",
        "camera.data.ortho_scale = 3.65": "camera.data.ortho_scale = 3.25",
        "IATF CUT007のPDCA診断フレーム生成を開始しました。": "IATF CUT007不合格のため、CUT008を実行しました。",
        "IATF CUT007診断フレーム生成OKです。": "IATF CUT008診断フレーム生成OKです。",
        "IATF CUT007診断フレーム生成NGのため、次PDCAが必要です。": "IATF CUT008診断フレーム生成NGのため、次PDCAが必要です。",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    with tempfile.TemporaryDirectory(prefix="iatf_cut008_bulma_") as tmp:
        script = Path(tmp) / "render_cut008.py"
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
