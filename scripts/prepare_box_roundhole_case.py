#!/usr/bin/env python3
"""Prepare a reproducible OpenFOAM box case from a template and audited mesh."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


def copy_tree_without_poly_mesh(src: Path, dst: Path) -> None:
    for name in ("0", "system"):
        shutil.copytree(src / name, dst / name)
    (dst / "constant").mkdir(parents=True, exist_ok=True)
    for item in (src / "constant").iterdir():
        if item.name != "polyMesh" and item.is_file():
            shutil.copy2(item, dst / "constant" / item.name)


def patch_velocity(path: Path, velocity: float) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = r"gate\s*\{\s*type\s+fixedValue;\s*value\s+uniform\s+\([^)]*\);\s*\}"
    replacement = f"gate {{ type fixedValue; value uniform ({velocity:g} 0 0); }}"
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise ValueError(f"gate velocity boundary not found in {path}")
    path.write_text(updated, encoding="utf-8")


def prepare(template: Path, mesh_case: Path, output: Path, velocity: float) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    copy_tree_without_poly_mesh(template, output)
    shutil.copytree(mesh_case / "constant" / "polyMesh", output / "constant" / "polyMesh")
    patch_velocity(output / "0" / "U", velocity)
    manifest = {
        "schema": "clawstack.box_roundhole_case_preflight.v1",
        "template": str(template),
        "mesh_case": str(mesh_case),
        "output": str(output),
        "gate_velocity_m_s": velocity,
        "boundary_contract": {"gate": "fixedValue velocity", "vent": "pressure outlet / inletOutlet alpha"},
        "status": "PREPARED_FOR_TRANSIENT_RUN",
    }
    (output / "case_preflight.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--mesh-case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--gate-velocity-m-s", type=float, default=8.0)
    a = p.parse_args()
    print(json.dumps(prepare(a.template, a.mesh_case, a.output, a.gate_velocity_m_s), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
