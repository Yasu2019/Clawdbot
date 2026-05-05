"""Render CUT_006 Bulma diagnostic frames using the CUT_005 Bulma probe.

This wrapper keeps the low-API rule: one cut, seven diagnostic frames, no
OpenCodeGo/DeepSeek, local Blender only.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/workspace/render_iatf_cut005_bulma_probe_once.py"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    replacements = {
        'ROOT = Path(__file__).resolve().parents[2]': f'ROOT = Path(r"{str(ROOT)}")',
        "CUT_005": "CUT_006",
        "cut005_bulma_probe": "cut006_bulma_probe",
        "iatf_cut005_bulma_probe": "iatf_cut006_bulma_probe",
        "cut005_bulma_": "cut006_bulma_",
        "verify packaging evidence": "compare QMI with current work card",
        "梱包工程を確認します。作業カード、QMI、箱の40個/50個表示、FIFOラベルを順に見せてください。": "はい。QMIで梱包指示を確認できますが、現場の作業カードが最新かどうかは、今ここで照合します。",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    with tempfile.TemporaryDirectory(prefix="iatf_cut006_bulma_") as tmp:
        script = Path(tmp) / "render_cut006.py"
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
