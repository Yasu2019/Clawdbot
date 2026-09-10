#!/usr/bin/env python3
"""Copy a case and scale its OpenFOAM mesh coordinates with transformPoints."""
from __future__ import annotations
import argparse, shutil, subprocess
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--scale", type=float, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise SystemExit(f"output already exists: {a.output}")
    shutil.copytree(a.base, a.output)
    cmd = ["docker", "run", "--rm", "-v", f"{a.output.resolve()}:/case",
           "opencfd/openfoam-dev:latest", "bash", "-lc",
           f"source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1; transformPoints -case /case -scale '({a.scale:g} {a.scale:g} {a.scale:g})'"]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
    (a.output / "mesh_scale.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise SystemExit(proc.returncode)
    print(f"created scaled case: {a.output} scale={a.scale:g}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
