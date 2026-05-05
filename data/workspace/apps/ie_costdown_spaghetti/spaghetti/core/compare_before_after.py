#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Before/After comparison for spaghetti analysis.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from spaghetti_analyzer import analyze


def read_summary(report_dir: Path):
    tag = pd.read_csv(report_dir / "tag_summary.csv")
    dwell = pd.read_csv(report_dir / "zone_dwell_summary.csv")
    patterns = pd.read_csv(report_dir / "waste_patterns.csv")
    return tag, dwell, patterns


def compare(before_csv, after_csv, layout, output):
    output = Path(output)
    before_dir = output / "before"
    after_dir = output / "after"
    analyze(before_csv, layout, before_dir)
    analyze(after_csv, layout, after_dir)
    b_tag, b_dwell, b_pat = read_summary(before_dir)
    a_tag, a_dwell, a_pat = read_summary(after_dir)

    rows = []
    for tag_id in sorted(set(b_tag["tag_id"]).union(set(a_tag["tag_id"]))):
        b = b_tag[b_tag["tag_id"] == tag_id].head(1)
        a = a_tag[a_tag["tag_id"] == tag_id].head(1)
        bd = float(b["distance_m"].iloc[0]) if not b.empty else 0.0
        ad = float(a["distance_m"].iloc[0]) if not a.empty else 0.0
        bt = float(b["duration_sec"].iloc[0]) if not b.empty else 0.0
        at = float(a["duration_sec"].iloc[0]) if not a.empty else 0.0
        reduction = (bd - ad) / bd if bd else 0.0
        rows.append({
            "tag_id": tag_id,
            "before_distance_m": round(bd, 3),
            "after_distance_m": round(ad, 3),
            "distance_reduction_m": round(bd - ad, 3),
            "distance_reduction_ratio": round(reduction, 4),
            "before_duration_sec": round(bt, 2),
            "after_duration_sec": round(at, 2),
            "before_patterns": len(b_pat[b_pat["tag_id"] == tag_id]) if not b_pat.empty else 0,
            "after_patterns": len(a_pat[a_pat["tag_id"] == tag_id]) if not a_pat.empty else 0,
        })

    comp = pd.DataFrame(rows)
    output.mkdir(parents=True, exist_ok=True)
    comp.to_csv(output / "before_after_comparison.csv", index=False, encoding="utf-8-sig")

    md = ["# 改善前後 スパゲッティ図比較レポート", ""]
    md.append("## 1. 改善前後サマリー")
    md.append(comp.to_markdown(index=False) if not comp.empty else "データなし")
    md.append("")
    md.append("## 2. 判定目安")
    md.append("- 歩行距離が20%以上減少：レイアウト改善効果あり")
    md.append("- ムダ動線候補が減少：置き場・外段取り化の効果あり")
    md.append("- 距離が減ってもCTが悪化：検査順序、品質確認、手元作業の再分析が必要")
    md.append("")
    md.append("## 3. OpenCodeGOレビュー指示")
    md.append("`opencodego/prompts/spaghetti_review_prompt.md` に比較CSVを添付してレビューさせてください。")
    (output / "comparison_report.md").write_text("\n".join(md), encoding="utf-8")
    return comp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    comp = compare(args.before, args.after, args.layout, args.output)
    print(comp.to_string(index=False))


if __name__ == "__main__":
    main()
