"""
Instagram post text validator for Japanese manufacturing/AI QA account.

Usage:
  python validate_post_text.py input_post.txt

This script is read-only toward external systems.
It only reads a local text file and prints a risk report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BLOCKED_PATTERNS = [
    r"絶対に稼げる",
    r"誰でも.*稼げる",
    r"月収[0-9０-９]+万.*保証",
    r"完全放置",
    r"100%成功",
    r"絶対安全",
    r"保証します",
    r"専門家不要",
    r"法律リスクゼロ",
    r"規約違反にならない",
]

CAUTION_PATTERNS = [
    r"必ず",
    r"絶対",
    r"誰でも簡単",
    r"完全自動",
    r"最強",
    r"唯一",
    r"世界一",
    r"公式",
    r"無料で稼ぐ",
    r"放置",
    r"ラクして",
    r"IATF",
    r"ISO",
    r"薬機法",
    r"景表法",
    r"著作権",
    r"顧客",
    r"取引先",
    r"品番",
]

def find_matches(text: str, patterns: list[str]) -> list[str]:
    hits = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_post_text.py input_post.txt")
        return 2

    p = Path(sys.argv[1])
    if not p.exists():
        print(f"ERROR: File not found: {p}")
        return 2

    text = p.read_text(encoding="utf-8")
    blocked = find_matches(text, BLOCKED_PATTERNS)
    caution = find_matches(text, CAUTION_PATTERNS)

    print("=== Instagram Post Risk Check ===")
    print(f"File: {p}")
    print(f"Length: {len(text)} characters")
    print("")

    if blocked:
        print("[REJECT] Blocked expressions found:")
        for h in blocked:
            print(f" - {h}")
    else:
        print("[OK] No blocked expressions found.")

    if caution:
        print("")
        print("[CAUTION] Expressions requiring human review:")
        for h in caution:
            print(f" - {h}")
    else:
        print("[OK] No caution expressions found.")

    print("")
    if blocked:
        print("Decision: rejected")
        return 1
    if caution:
        print("Decision: needs_human_review")
        return 0
    print("Decision: likely_ok_but_human_approval_required")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
