#!/usr/bin/env python3
"""Enable the compiled crossWLFViscosityModel in an OpenFOAM case."""
from __future__ import annotations
import argparse
from pathlib import Path


DICT = """FoamFile { version 2.0; format ascii; class dictionary; object momentumTransport; }
libs (\"libcrossWLFViscosityModel.so\");
simulationType laminar;
laminar
{
    model generalizedNewtonian;
    viscosityModel crossWLFViscosityModel;
    crossWLFViscosityModelCoeffs
    {
        n 0.65;
        tauStar 55.6;
        D1 1.0e10;
        D2 378.15;
        D3 0;
        A1 17.44;
        A2 51.6;
        rhoFloor 1e-9;
    }
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, required=True)
    args = ap.parse_args()
    path = args.case / "constant" / "momentumTransport"
    path.write_text(DICT, encoding="utf-8")
    print(f"enabled custom Cross-WLF model in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
