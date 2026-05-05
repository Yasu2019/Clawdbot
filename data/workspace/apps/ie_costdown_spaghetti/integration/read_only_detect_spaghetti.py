#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存ミニPC環境のスパゲッティ図解析対応状況を読み取り専用で確認するスクリプト。
既存ファイルを変更しません。
"""
import argparse
import os
from pathlib import Path

KEYWORDS = [
    "spaghetti",
    "spaghetti_diagram",
    "movement_trace",
    "trajectory",
    "uwb",
    "rssi",
    "position",
    "xy_trace",
    "heatmap",
    "動線",
    "スパゲッティ",
]

def scan(root: Path, max_files=20000):
    hits = []
    count = 0
    for p in root.rglob("*"):
        if count > max_files:
            break
        if p.is_file():
            count += 1
            name = p.name.lower()
            if any(k.lower() in name for k in KEYWORDS):
                hits.append(str(p))
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="scan root")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    hits = scan(root)
    print("# Spaghetti Existing Implementation Scan")
    print(f"root: {root}")
    print(f"hits: {len(hits)}")
    for h in hits[:200]:
        print(h)

    if hits:
        print("\n判定案: HOLD_OR_ADAPTER_ONLY")
        print("理由: 既存の動線/スパゲッティ/測位系実装候補があるため、内容確認後に融合判断。")
    else:
        print("\n判定案: ADD_NEW_MODULE")
        print("理由: スパゲッティ図分析コード候補が見つからないため、新規追加が妥当。")

if __name__ == "__main__":
    main()
