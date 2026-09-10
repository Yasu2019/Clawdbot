#!/usr/bin/env python3
"""Create a solver case with the mesh from another OpenFOAM case."""
from __future__ import annotations
import argparse, shutil
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--mesh-case", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise SystemExit(f"output already exists: {a.output}")
    shutil.copytree(a.base, a.output)
    dst = a.output / "constant" / "polyMesh"
    shutil.rmtree(dst)
    shutil.copytree(a.mesh_case / "constant" / "polyMesh", dst)
    print(f"created mesh variant: {a.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
