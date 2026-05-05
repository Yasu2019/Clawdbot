"""
Generate a basic Instagram content calendar CSV.

Usage:
  python generate_content_calendar.py

No external calls. No posting.
"""

from __future__ import annotations

import csv
from pathlib import Path
from datetime import date, timedelta

themes = [
    ("不良率を安全に見える化する3ステップ", "carousel", "保存型"),
    ("AIエージェントでDBを壊さないためのルール", "carousel", "失敗回避型"),
    ("品質保証でChatGPTを使う前に決めるべきこと", "reel", "教育型"),
    ("IATF内部監査で記録類を確認するコツ", "carousel", "実務型"),
    ("今週のOpenClaw改善メモ", "story", "開発記録型"),
]

def main() -> None:
    out = Path("content_calendar_generated.csv")
    start = date.today()
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "status", "theme", "format", "category", "target",
            "cta", "human_approval", "risk_notes"
        ])
        for i, (theme, fmt, cat) in enumerate(themes):
            writer.writerow([
                (start + timedelta(days=i)).isoformat(),
                "idea",
                theme,
                fmt,
                cat,
                "製造業の品質保証・現場改善担当者",
                "プロフィールの無料テンプレへ",
                "required",
                "誇大表現・社内機密・規格断定に注意"
            ])
    print(f"Wrote: {out.resolve()}")

if __name__ == "__main__":
    main()
