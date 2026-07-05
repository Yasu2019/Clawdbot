# -*- coding: utf-8 -*-
"""U4: 自動リターゲット(S6) — skill_pipeline_implementation_spec.md 準拠。

status=="retarget_ready" の依頼の reference.bvh を bvh_retarget.py に通し、
C:\v50_work\refs\<skill_name>.json を生成。period_sec が 0.6〜2.5 秒に入れば
status="retargeted"+ref_path 記入。範囲外/失敗は needs_human_source(escalate)。

usage: python u4_retarget_runner.py --once
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\skill_requests.json"
RETARGETER = os.path.join(HERE, "..", "stage_b", "bvh_retarget.py")
REFS_DIR = r"C:\v50_work\refs"
PERIOD_MIN, PERIOD_MAX = 0.6, 2.5


def retarget(bvh, skill):
    os.makedirs(REFS_DIR, exist_ok=True)
    out = os.path.join(REFS_DIR, f"{skill}.json")
    r = subprocess.run([sys.executable, RETARGETER, "--bvh", bvh, "--out", out],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=os.path.dirname(RETARGETER))
    if r.returncode != 0:
        raise RuntimeError(f"retargeter rc={r.returncode}: {(r.stderr or '')[-300:]}")
    d = json.load(open(out, encoding="utf-8"))
    period = float(d["period_sec"])
    if not (PERIOD_MIN <= period <= PERIOD_MAX):
        raise ValueError(f"period {period}s outside [{PERIOD_MIN},{PERIOD_MAX}]")
    return out, period, float(d["clip_vx_mps"])


def run_once():
    if not os.path.exists(STORE):
        print("no queue file"); return 0
    data = json.load(open(STORE, encoding="utf-8"))
    changed = 0
    for req in data.get("requests", []):
        if req.get("status") != "retarget_ready":
            continue
        skill = (req.get("interpretation") or {}).get("skill_name", "unknown")
        bvh = (req.get("reference") or {}).get("bvh")
        if not bvh or not os.path.exists(bvh):
            req["status"] = "needs_human_source"
            req["notes"] = "U4: reference.bvh が無い/存在しない"
        else:
            try:
                out, period, vx = retarget(bvh, skill)
                req["ref_path"] = out
                req["ref_stats"] = {"period_sec": period, "clip_vx_mps": vx}
                req["status"] = "retargeted"
            except Exception as e:
                req["status"] = "needs_human_source"
                req["notes"] = f"U4: retarget failed: {type(e).__name__}: {str(e)[:200]}"
        req["retargeted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        changed += 1
        print(f"U4 {req['id']}: {skill} -> {req['status']}"
              + (f" ({req.get('ref_path')}, period={req.get('ref_stats',{}).get('period_sec')}s)"
                 if req.get("ref_path") else f" [{req.get('notes','')}]"))
    if changed:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"U4 done: {changed} request(s) processed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.parse_args()
    raise SystemExit(run_once())
