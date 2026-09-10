#!/usr/bin/env python3
"""Add OpenFOAM volume-integral diagnostics to a case controlDict."""
from __future__ import annotations
import argparse
from pathlib import Path

BLOCK = r'''

functions
{
    totalMass
    {
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        fields          (rho);
        operation       volIntegrate;
        writeFields     false;
    }
    polymerVolume
    {
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        fields          (alpha.polymer);
        operation       volIntegrate;
        writeFields     false;
    }
    thermalIntegral
    {
        type            volFieldValue;
        libs            ("libfieldFunctionObjects.so");
        fields          (T);
        operation       volIntegrate;
        writeFields     false;
    }
}
'''

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, required=True)
    args = ap.parse_args()
    p = args.case / "system" / "controlDict"
    text = p.read_text(encoding="utf-8")
    if "totalMass" not in text:
        text += BLOCK
    p.write_text(text, encoding="utf-8")
    print(f"conservation function objects enabled in {p}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
