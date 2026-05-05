#!/usr/bin/env python3
"""Create a simple review report skeleton for CAD-to-AI-video outputs."""
import argparse, datetime
from pathlib import Path

TEMPLATE = """# CAD/AI動画レビュー報告書

作成日時: {ts}
プロジェクト: {project}

## 入力

- 元CAD/CAE/Blenderガイド動画: 未記入
- Pass1: 未記入
- Pass2: 未記入
- Pass3: 未記入
- 使用設定: 未記入

## 判定

- [ ] 元形状の意図が維持されている
- [ ] 部品数・穴・主要特徴が変わっていない
- [ ] 工程順序が変わっていない
- [ ] 寸法・注記は後処理で正しく追加されている
- [ ] AI動画が正式な設計証拠ではないことを明記している
- [ ] 社外提示可否を確認した

## コメント

未記入

## 最終判断

- [ ] 採用
- [ ] 修正後採用
- [ ] 不採用
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default='sample_project')
    ap.add_argument('--out', default='reports/review_report.md')
    args = ap.parse_args()
    text = TEMPLATE.format(ts=datetime.datetime.now().isoformat(timespec='seconds'), project=args.project)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='utf-8')
    print(f"Review report written: {out}")

if __name__ == '__main__':
    main()
