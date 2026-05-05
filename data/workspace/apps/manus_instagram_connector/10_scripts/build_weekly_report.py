"""
Build a simple weekly KPI report from CSV.

Input CSV columns:
post_id,title,format,reach,likes,saves,shares,comments,profile_visits,link_clicks

Usage:
  python build_weekly_report.py insights.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from datetime import datetime

def pct(num: float, den: float) -> float:
    return 0.0 if den == 0 else round(num / den * 100, 2)

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python build_weekly_report.py insights.csv")
        return 2

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"ERROR: File not found: {src}")
        return 2

    rows = []
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            for k in ["reach", "likes", "saves", "shares", "comments", "profile_visits", "link_clicks"]:
                r[k] = int(r.get(k) or 0)
            r["save_rate"] = pct(r["saves"], r["reach"])
            r["share_rate"] = pct(r["shares"], r["reach"])
            r["comment_rate"] = pct(r["comments"], r["reach"])
            r["profile_visit_rate"] = pct(r["profile_visits"], r["reach"])
            r["link_click_rate"] = pct(r["link_clicks"], r["profile_visits"])
            rows.append(r)

    rows_by_save = sorted(rows, key=lambda x: x["save_rate"], reverse=True)
    rows_by_share = sorted(rows, key=lambda x: x["share_rate"], reverse=True)

    out = Path("weekly_kpi_report_generated.md")
    lines = [
        "# Weekly Instagram KPI Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        f"- Posts analyzed: {len(rows)}",
        f"- Total reach: {sum(r['reach'] for r in rows)}",
        f"- Total saves: {sum(r['saves'] for r in rows)}",
        f"- Total shares: {sum(r['shares'] for r in rows)}",
        f"- Total link clicks: {sum(r['link_clicks'] for r in rows)}",
        "",
        "## Top posts by save rate",
        "",
    ]

    for r in rows_by_save[:3]:
        lines.append(f"- {r.get('title','')}: save_rate={r['save_rate']}%, reach={r['reach']}, saves={r['saves']}")

    lines += ["", "## Top posts by share rate", ""]
    for r in rows_by_share[:3]:
        lines.append(f"- {r.get('title','')}: share_rate={r['share_rate']}%, reach={r['reach']}, shares={r['shares']}")

    lines += [
        "",
        "## Next actions",
        "",
        "- 保存率が高いテーマを次週カルーセル化する。",
        "- リンククリック率が低い場合はプロフィール文とCTAを見直す。",
        "- 誇大表現・機密情報・規約違反がないか投稿前レビューを継続する。",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {out.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
