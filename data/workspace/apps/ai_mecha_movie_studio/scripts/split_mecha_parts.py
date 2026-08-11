# -*- coding: utf-8 -*-
"""分割済みメカFBXに膝・肘を作る（剛体リグの前工程）。

剛体ペアレントは 1部品=1ボーン が前提のため、関節をまたぐ部品が残っていると
その関節は曲がらない。切断位置は断面が最も細い場所を自動探索する。

  python scripts/split_mecha_parts.py \
      --model "D:/Clawdbot_Docker_20260125/Gundam/FLB/Zaku_Segmentation.fbx" \
      --cuts presets/zaku_segmentation_cuts.json \
      --out workspace/sample_mecha_movie/reference/zaku_split/Zaku_Split.fbx
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mecha_studio.adapters import blender  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="メカ部品を膝・肘で分割する")
    ap.add_argument("--model", required=True, help="分割済みFBX（部品ごとに別オブジェクト）")
    ap.add_argument("--cuts", required=True, help="切断指定JSON")
    ap.add_argument("--out", required=True, help="出力FBX")
    ap.add_argument("--report", help="結果JSON（既定は出力FBXと同じ場所）")
    a = ap.parse_args(argv)

    def resolve(p):
        q = Path(p)
        return q if q.is_absolute() else ROOT / q

    out = resolve(a.out)
    report = resolve(a.report) if a.report else out.with_name(out.stem + "_report.json")

    print(f"blender: {blender.available()}")
    blender.split_parts(resolve(a.model), resolve(a.cuts), out, report)

    if report.exists():
        r = json.loads(report.read_text(encoding="utf-8"))
        print(f"\n部品数: {r['input_parts']} -> {r['output_parts']}")
        ng = [c for c in r["cuts"] if c.get("status") != "ok"]
        for c in r["cuts"]:
            if c.get("status") != "ok":
                print(f"  {c['part']:8} {c.get('status')}")
            elif c.get("mode") == "islands":
                groups = ", ".join(f"{k}*{v}" for k, v in (c.get("groups") or {}).items())
                print(f"  {c['part']:8} islands {c['axis']} -> {c['islands']}島 ({groups})")
            else:
                res = " / ".join(f"{x['name']}({x['verts']}v)" for x in c["results"])
                print(f"  {c['part']:8} {c['axis']} at={c['at_normalized']:.3f} -> {res}")
        if ng:
            print(f"\n⚠ 失敗/要確認: {len(ng)} 件")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
