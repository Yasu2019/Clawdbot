#!/usr/bin/env python3
"""Convert a shotlist CSV into prompt text files for CAD/ComfyUI video workflows."""
import csv
import argparse
from pathlib import Path

POSITIVE_BASE = "日本の製造業向けの説明動画。CAD由来の構造を維持し、清潔な工場照明、見やすい陰影、教育資料として理解しやすい映像。"
NEGATIVE_BASE = "寸法文字の変形、部品数の増減、穴の消失、形状の溶け、読めない文字、過度な反射、余計な人物。"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='examples/shotlist_sample.csv')
    ap.add_argument('--out', default='outputs/prompts')
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.csv, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row.get('shot_id', 'shot')
            purpose = row.get('purpose', '')
            subject = row.get('subject', '')
            motion = row.get('motion', '')
            notes = row.get('notes', '')
            text = f"""# {sid}

## Positive
{POSITIVE_BASE}
目的: {purpose}
対象: {subject}
動き: {motion}
注意: {notes}

## Negative
{NEGATIVE_BASE}

## Rule
寸法・ラベルは後処理で追加する。AI動画で設計判断しない。
"""
            (out_dir / f"{sid}_prompt.md").write_text(text, encoding='utf-8')
    print(f"Prompt files created: {out_dir}")

if __name__ == '__main__':
    main()
