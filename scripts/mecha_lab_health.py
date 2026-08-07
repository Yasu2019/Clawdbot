# -*- coding: utf-8 -*-
"""Mecha Motion Lab の「実際の稼働状態」を1枚のJSONに集約する。2026-08-08 導入。

背景: ダッシュボードは supervisor_status.json しか見ておらず、
state=escalated のまま209時間停止していても画面には「準備中」としか出なかった。
ブラウザからは プロセス生存 / GPU / チェックポイント資産 を見られないため、
ここで収集して lab_health.json に書き出す。

出力: data/workspace/apps/mecha_motion_lab/lab_health.json

usage:
  python scripts/mecha_lab_health.py          # 1回収集して書き出す
  python scripts/mecha_lab_health.py --print  # 標準出力にも出す
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
MECHA = REPO / "data" / "workspace" / "apps" / "mecha_motion_lab"
OUT = MECHA / "lab_health.json"
SUP_STATUS = MECHA / "supervisor_status.json"
CYCLE_DIR = Path(r"C:\v50_work\autonomy\walk_auto_cycle01")
KNOWN_GOOD = Path(r"C:\v50_work\autonomy\known_good")

sys.path.insert(0, str(REPO / "scripts"))
try:
    import gpu_arbiter
except Exception:
    gpu_arbiter = None

DEAD_AFTER_HOURS = 12.0


def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def hours_since(updated_at) -> float | None:
    if not updated_at:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            t = time.mktime(time.strptime(str(updated_at)[:19], fmt))
            return round((time.time() - t) / 3600.0, 2)
        except Exception:
            continue
    return None


def learning_processes() -> dict:
    """学習系プロセスの生存。列挙できなければ alive=None(不明)。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match "
             "'train_v50_walk_tracking|motion_learning_supervisor' } | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 3"],
            capture_output=True, text=True, timeout=90)
        raw = (r.stdout or "").strip()
        if not raw:
            return {"alive": False, "count": 0, "items": []}
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        items = [{"pid": d.get("ProcessId"),
                  "kind": ("trainer" if "train_v50_walk_tracking" in (d.get("CommandLine") or "")
                           else "supervisor")}
                 for d in data]
        return {"alive": len(items) > 0, "count": len(items), "items": items}
    except Exception as e:
        return {"alive": None, "count": None, "error": f"{type(e).__name__}: {e}"}


def known_good_checkpoints() -> list:
    """実在するチェックポイント資産。VERIFIED/ADOPTED はファイル名の規約で判定する。"""
    out = []
    if not KNOWN_GOOD.is_dir():
        return out
    for p in sorted(KNOWN_GOOD.glob("*.pt")):
        st = p.stat()
        name = p.name
        out.append({
            "name": name,
            "mb": round(st.st_size / 1024 / 1024, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
            "verified": "VERIFIED" in name or "ADOPTED" in name,
        })
    out.sort(key=lambda x: x["modified"], reverse=True)
    return out


def gpu_state() -> dict:
    if gpu_arbiter is None:
        return {"available": False}
    free, total = gpu_arbiter.gpu_memory()
    lease = gpu_arbiter.read_lease()
    live = gpu_arbiter.lease_is_live(lease)
    return {
        "available": True,
        "free_mb": free,
        "total_mb": total,
        "lease_owner": (lease or {}).get("owner") if live else None,
        "lease_expires_at": (lease or {}).get("expires_at") if live else None,
        "lease_priority": (lease or {}).get("priority") if live else None,
    }


def build() -> dict:
    sup = _read_json(SUP_STATUS) or {}
    age = hours_since(sup.get("updated_at"))
    procs = learning_processes()
    train = _read_json(CYCLE_DIR / "status.json") or {}

    if not sup:
        health, label = "unknown", "supervisor_status.json が読めません"
    elif procs.get("alive"):
        health, label = "running", "学習プロセス稼働中"
    elif age is not None and age >= DEAD_AFTER_HOURS and sup.get("state") in (
            "running", "training", "checking", "escalated"):
        health, label = "dead", f"{age:.1f} 時間更新なし・プロセス不在"
    elif sup.get("state") == "escalated":
        health, label = "escalated", "人間の判断待ち(エスカレーション)"
    else:
        health, label = "idle", f"state={sup.get('state')}"

    return {
        "schema": "clawstack.mecha_lab_health.v1",
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "health": health,
        "health_label": label,
        "supervisor": {
            "skill": sup.get("skill"),
            "state": sup.get("state"),
            "cycle": sup.get("cycle"),
            "cycles_recorded": len(sup.get("history", [])),
            "updated_at": sup.get("updated_at"),
            "hours_since_update": age,
            "escalation_reason": sup.get("escalation_reason"),
            "current_dir": sup.get("current_dir"),
        },
        "processes": procs,
        "training_progress": {
            "iteration": train.get("iteration"),
            "iterations_total": train.get("iterations_total"),
            "mean_reward_per_step": train.get("mean_reward_per_step"),
            "best_reward_per_step": train.get("best_reward_per_step"),
            "upright": train.get("upright"),
            "vx_mean": train.get("vx_mean"),
            "n_envs": train.get("n_envs"),
            "elapsed_sec": train.get("elapsed_sec"),
        } if train else None,
        "gpu": gpu_state(),
        "known_good": known_good_checkpoints(),
        # T066: 8スキルカードを埋めていた ml_supervisor.py は撤去済み。
        # 現supervisorは martial/care/artistic/rhythmic を一切出力しない。
        "scenario_cards_backed_by_real_data": False,
        "scenario_cards_note": (
            "martial/care/artistic/rhythmic の指標は 2026-07-14 に撤去されたモック"
            "(ml_supervisor.py.RETIRED_T066)が生成していたもの。現行の"
            "motion_learning_supervisor は skill/state/cycle/history のみを出力するため、"
            "これらのカードは実データでは埋まらない。"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="do_print")
    a = ap.parse_args()
    data = build()
    MECHA.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, OUT)
    print(f"書き出し: {OUT}  health={data['health']} ({data['health_label']})")
    if a.do_print:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
