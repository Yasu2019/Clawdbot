#!/usr/bin/env python3
import re
import sys
from pathlib import Path

patterns = [
    (r"(顧客名|客先)[:：]?\s*\S+", r"\1: [MASKED]"),
    (r"品番[:：]?\s*[A-Za-z0-9_\-]+", "品番: [MASKED]"),
    (r"図面番号[:：]?\s*[A-Za-z0-9_\-]+", "図面番号: [MASKED]"),
    (r"ロット(?:番号)?[:：]?\s*[A-Za-z0-9_\-]+", "ロット番号: [MASKED]"),
]

def mask(s):
    for p, r in patterns:
        s = re.sub(p, r, s)
    return s

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: mask_confidential_text.py input.txt [output.txt]")
        sys.exit(1)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) >= 3 else inp.with_suffix(".masked.txt")
    out.write_text(mask(inp.read_text(encoding="utf-8")), encoding="utf-8")
    print(out)
