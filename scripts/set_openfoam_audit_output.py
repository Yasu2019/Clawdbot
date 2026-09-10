#!/usr/bin/env python3
"""Set a guaranteed final write for short OpenFOAM audit runs."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, required=True)
    ap.add_argument("--interval", type=float, required=True)
    a = ap.parse_args()
    p = a.case / "system" / "controlDict"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"writeInterval\s+[^;]+;", f"writeInterval {a.interval:g};", s)
    p.write_text(s, encoding="utf-8")
    print(f"writeInterval={a.interval:g} in {p}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
