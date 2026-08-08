# -*- coding: utf-8 -*-
"""known_good/ のチェックポイントを現環境で再検証し、生きているものを棚卸しする。

2026-08-08 導入。背景(実測):
  known_good/walk_rsl_20260724_survival0.82_travel2.37.pt は記録では
  survival 0.817 / clean_travel 2.373m / fell=false だったが、現環境で走らせると
  travel -1.767m / 1.3秒で転倒 / min_upright 0.0 で、フレーム目視でも後方転倒だった。
  原因は 7/24 以降に v50_walk_env.py が7回改変(+未コミット96行)され、観測・報酬・地形が
  変わったこと。**チェックポイントは学習時の環境とセットでしか意味を持たない**。
  記録済みの数字は「その時の環境での値」であり、現在の資産価値を示さない。

方式:
  - ckpt形式を state_dict から自動判別する
      v1  : 'actor.0.weight' を持つ  -> render_walk.py (obs46)
      rsl : 'model_state_dict' を持つ -> render_walk_rsl.py
            入力次元 189=平地 / 200=地形スキャン付き(--height-scan 必須)
  - ファイル名から地形を推測して --terrain に渡す(slope/stairs/descent/corridor)
  - T067の罠を回避: --no-dr --no-reset --no-push を必ず付ける
    (1envレンダはDRが単一サンプルになり不利な質量を引くと実力を過小評価する)
  - 結果は JSON と表で出力。判定は fell / travel / min_upright の実測で行い、
    ファイル名の VERIFIED 表記は信用しない

usage:
  python scripts/verify_known_good_ckpts.py --list
  python scripts/verify_known_good_ckpts.py --only walk_rsl_natural_gait_ADOPTED
  python scripts/verify_known_good_ckpts.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
STAGE_A = REPO / "projects" / "AtsugiMechaCity" / "rl_integration" / "stage_a"
KNOWN_GOOD = Path(r"C:\v50_work\autonomy\known_good")
OUT_ROOT = Path(r"C:\v50_work\verify_known_good_20260808")
PY = r"C:\v50_work\genesis_venv\Scripts\python.exe"
REPORT = REPO / "data" / "workspace" / "apps" / "mecha_motion_lab" / "known_good_verification.json"
TIMEOUT = 1800


def detect(ckpt: Path) -> dict:
    """(形式, 観測次元) を state_dict から判定する。"""
    import torch
    d = torch.load(ckpt, map_location="cpu", weights_only=False)
    if not isinstance(d, dict):
        return {"fmt": "?", "obs": None}
    if "model_state_dict" in d:
        sd = d["model_state_dict"]
        obs = None
        for k, v in sd.items():
            if k.endswith("weight") and hasattr(v, "shape") and len(v.shape) == 2:
                obs = int(v.shape[1])
                break
        return {"fmt": "rsl", "obs": obs}
    if any("actor" in str(k) for k in d):
        return {"fmt": "v1", "obs": 46}
    return {"fmt": "?", "obs": None}


def guess_terrain(name: str) -> str | None:
    n = name.lower()
    if "corridor" in n:
        return "corridor"
    if "descent" in n:
        return "slope_down"
    if "stairs" in n:
        return "stairs"
    if "slope" in n:
        return "slope_up"
    return None


def run_one(ckpt: Path, seconds: int) -> dict:
    info = detect(ckpt)
    out = OUT_ROOT / ckpt.stem
    out.mkdir(parents=True, exist_ok=True)
    terrain = guess_terrain(ckpt.name)
    rec: dict = {"ckpt": ckpt.name, "fmt": info["fmt"], "obs": info["obs"],
                 "terrain": terrain or "none"}

    if info["fmt"] == "v1":
        cmd = [PY, str(STAGE_A / "render_walk.py"), "--ckpt", str(ckpt),
               "--out", str(out), "--seconds", str(seconds)]
    elif info["fmt"] == "rsl":
        cmd = [PY, str(STAGE_A / "render_walk_rsl.py"), "--ckpt", str(ckpt),
               "--out", str(out), "--seconds", str(seconds),
               "--no-dr", "--no-reset", "--no-push", "--every", "40"]
        if info["obs"] == 200:
            cmd.append("--height-scan")   # 次元不一致を避けるため必須
        if terrain:
            cmd += ["--terrain", terrain]
    else:
        rec["status"] = "unknown_format"
        return rec

    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT, cwd=str(STAGE_A))
        stdout = r.stdout or ""
        m = re.search(r"WALK_CHECK:\s*(\{.*\})", stdout)
        if m:
            rec.update(json.loads(m.group(1)))
            rec["status"] = "ok"
        else:
            rec["status"] = "no_walk_check"
            rec["stderr_tail"] = (r.stderr or "")[-400:]
    except subprocess.TimeoutExpired:
        rec["status"] = "timeout"
    except Exception as e:
        rec["status"] = f"error: {type(e).__name__}: {e}"
    rec["elapsed_sec"] = round(time.time() - t0, 1)
    return rec


def verdict(rec: dict) -> str:
    """ファイル名のVERIFIED表記ではなく実測で判定する。"""
    if rec.get("status") != "ok":
        return "測定不能"
    fell = rec.get("fell", True)
    travel = rec.get("final_travel_m", rec.get("final_travel", 0.0)) or 0.0
    upright = rec.get("min_upright", 0.0) or 0.0
    if not fell and travel >= 1.0:
        return "生存(歩行成立)"
    if not fell and travel < 1.0:
        return "立つが進まない"
    if upright <= 0.05:
        return "完全転倒"
    return "転倒"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="ファイル名に含む文字列で絞る")
    ap.add_argument("--seconds", type=int, default=8)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    ckpts = sorted(KNOWN_GOOD.glob("*.pt"))
    if a.only:
        ckpts = [c for c in ckpts if a.only in c.name]
    if a.list:
        for c in ckpts:
            i = detect(c)
            print(f"  {c.name:<58} fmt={i['fmt']} obs={i['obs']} terrain={guess_terrain(c.name)}")
        return 0

    print(f"検証対象: {len(ckpts)} 件 (1件あたり数分)")
    results = []
    for i, c in enumerate(ckpts, 1):
        print(f"\n[{i}/{len(ckpts)}] {c.name}")
        rec = run_one(c, a.seconds)
        rec["verdict"] = verdict(rec)
        results.append(rec)
        print(f"    -> {rec['verdict']}  fell={rec.get('fell')} "
              f"travel={rec.get('final_travel_m', rec.get('final_travel'))} "
              f"min_upright={rec.get('min_upright')} ({rec.get('elapsed_sec')}s)")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(
            {"schema": "clawstack.known_good_verification.v1",
             "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "note": "現環境での実測。ファイル名のVERIFIED表記は当時の環境の値であり信用しない",
             "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 結果 ===")
    for r in results:
        print(f"  {r['verdict']:<14} {r['ckpt']}")
    alive = [r for r in results if r["verdict"] == "生存(歩行成立)"]
    print(f"\n生存: {len(alive)} / {len(results)} 件")
    print(f"レポート: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
