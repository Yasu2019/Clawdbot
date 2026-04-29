#!/usr/bin/env python3
import argparse
import os
import re
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

MASK_PATTERNS = [
    (r"品番[:：]?\s*[A-Za-z0-9_\-]+", "品番: [MASKED]"),
    (r"図面番号[:：]?\s*[A-Za-z0-9_\-]+", "図面番号: [MASKED]"),
    (r"ロット番号[:：]?\s*[A-Za-z0-9_\-]+", "ロット番号: [MASKED]"),
]

def load_yaml(path: Path):
    text = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text)
    # minimal fallback for simple key-value yaml
    data = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
    return data

def mask_text(text: str) -> str:
    for pattern, repl in MASK_PATTERNS:
        text = re.sub(pattern, repl, text)
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    data = load_yaml(Path(args.input))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    title = data.get("title", "品質教育動画")
    audience = data.get("audience", "製造現場")
    process = data.get("process", "工程")
    defect_type = data.get("defect_type", "不具合")
    objective = data.get("objective", "現場で正しい判断ができるようにする")
    key_points = data.get("key_points") or data.get("must_include") or []

    script = f"""# {title} 台本

対象者: {audience}
工程: {process}
テーマ: {defect_type}
目的: {objective}

## 導入
[落ち着いた声] 今日のテーマは「{title}」です。現場で発見したときに、何を見て、誰に伝え、どのように記録するかを確認します。

## NG例
[注意を促す声] 不具合を見つけても、自己判断で流してしまうことは危険です。小さな異常でも、後工程やお客様で大きな問題になる可能性があります。

## 重要ポイント
"""
    for i, p in enumerate(key_points, 1):
        script += f"{i}. {p}\n"
    script += """
## まとめ
[強調] 見つけたら、止める・確認する・記録する。この3つを徹底してください。
"""
    script = mask_text(script)

    storyboard = f"""# {title} 絵コンテ

| Scene | 内容 | 映像 | テロップ |
|---|---|---|---|
| 1 | 導入 | 清潔な工場背景とAIアバター | 今日のテーマ |
| 2 | NG例 | {defect_type}の模式図 | 自己判断で流さない |
| 3 | 原因 | 工程・材料・設備・検査の4要因図 | 原因は複合要因で見る |
| 4 | 対策 | 作業者が確認している様子 | 止める・確認する・記録する |
| 5 | まとめ | アバターが要点を再確認 | 現場判断を標準化 |
"""

    vids_prompt = f"""# Google Vids貼り付け用プロンプト

製造業の品質教育動画を作成してください。
タイトル: {title}
対象者: {audience}
動画の雰囲気: 清潔な工場、落ち着いた品質教育、実務的
禁止事項: 顧客名、品番、図面番号、ロット番号、個人名は表示しない

## シーン構成
{storyboard}

## ナレーション
{script}

## BGM
控えめで清潔感のある教育動画向けBGM。ナレーションを邪魔しない。
"""

    review = f"""# {title} レビューシート

- [ ] 技術内容は正しい
- [ ] 顧客名・品番・図面番号・ロット番号がない
- [ ] 現場標準と矛盾しない
- [ ] 誇張表現がない
- [ ] 品質保証責任者が確認した
"""

    audit = {
        "title": title,
        "audience": audience,
        "process": process,
        "defect_type": defect_type,
        "masking_required": data.get("masking_required", True),
        "human_approval_required": True,
        "outputs": ["script.md", "storyboard.md", "google_vids_prompt.md", "review_sheet.md"]
    }

    (out / "script.md").write_text(script, encoding="utf-8")
    (out / "storyboard.md").write_text(storyboard, encoding="utf-8")
    (out / "google_vids_prompt.md").write_text(vids_prompt, encoding="utf-8")
    (out / "review_sheet.md").write_text(review, encoding="utf-8")
    (out / "audit_trace.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated package: {out}")

if __name__ == "__main__":
    main()
