#!/usr/bin/env python3
"""Simple router stub for OpenClaw CAD/Video workflows."""
import argparse, json, re
from pathlib import Path

ROUTES = [
    (r"DXF|押し出し|extrude", "FreeCAD macro", "DXF to Sketch/extrude"),
    (r"治具|ブラケット|部品|寸法|STEP", "CadQuery/FreeCAD", "Parametric CAD"),
    (r"工場|レイアウト|棚|部屋|建築", "Blender; SketchUp optional", "Rough layout"),
    (r"歩行|人型|リグ|BVH|Mixamo|Rokoko", "Blender", "Motion guide"),
    (r"動画|説明|教育|提案|V2V|ComfyUI|LTX", "ComfyUI LTX 3-Pass after CAD guide", "Video finish"),
]

def decide(text):
    for pattern, tool, reason in ROUTES:
        if re.search(pattern, text, re.IGNORECASE):
            return {"tool": tool, "reason": reason, "ue5_allowed": False, "human_review_required": True}
    return {"tool": "Human review first", "reason": "Ambiguous request", "ue5_allowed": False, "human_review_required": True}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=None)
    ap.add_argument('--text', default=None)
    args = ap.parse_args()
    if args.input and Path(args.input).exists():
        data = json.loads(Path(args.input).read_text(encoding='utf-8'))
        text = json.dumps(data, ensure_ascii=False)
    else:
        text = args.text or "工場レイアウトを説明動画にしたい"
    print(json.dumps(decide(text), ensure_ascii=False, indent=2))
