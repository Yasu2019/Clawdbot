# -*- coding: utf-8 -*-
"""U5: 学習ディスパッチ(S8) — skill_pipeline_implementation_spec.md 準拠。

(a) dispatch: status=="retargeted" の依頼を1件だけ選び、supervisor をdetached起動。
    GPU1枚のため同時学習は1スキルまで(supervisor_status.json の state と
    genesisプロセス数で判定)。起動したら status="training"。
(b) sync: supervisor_status.json の skill が training 中の依頼と一致し、
    state が learned/escalated なら依頼側 status に反映。

usage: python u5_train_dispatcher.py --once [--dry-run]
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\skill_requests.json"
SUP_STATUS = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\supervisor_status.json"
SUPERVISOR = os.path.join(HERE, "motion_learning_supervisor.py")
TRAIN_ARGS = ["--iterations", "3000", "--entropy", "0.002", "--init-log-std", "-0.9"]


def sup_state():
    if not os.path.exists(SUP_STATUS):
        return None
    try:
        return json.load(open(SUP_STATUS, encoding="utf-8"))
    except Exception:
        return None


def gpu_busy():
    """学習中判定: supervisorのstateが進行系、または学習系pythonが2本以上。"""
    s = sup_state()
    if s and s.get("state") in ("running", "training", "checking"):
        return True, f"supervisor busy: skill={s.get('skill')} state={s.get('state')}"
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                            "Where-Object { $_.CommandLine -match 'train_v50_walk_tracking|motion_learning_supervisor' } "
                            "| Measure-Object).Count"],
                           capture_output=True, text=True, timeout=60)
        if int((r.stdout or "0").strip() or 0) >= 1:
            return True, "trainer/supervisor process alive"
    except Exception:
        pass
    return False, "idle"


def run_once(dry):
    if not os.path.exists(STORE):
        print("no queue file"); return 0
    data = json.load(open(STORE, encoding="utf-8"))
    changed = 0

    # (b) sync: 完了/エスカレーションの反映
    s = sup_state()
    if s and s.get("state") in ("learned", "escalated"):
        for req in data.get("requests", []):
            if req.get("status") == "training" and \
               (req.get("training") or {}).get("supervisor_skill") == s.get("skill"):
                req["status"] = "learned" if s["state"] == "learned" else "escalated"
                req["training"]["result_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                changed += 1
                print(f"U5 sync {req['id']}: -> {req['status']} (supervisor {s['skill']})")

    # (a) dispatch: 空きGPUに1件だけ投入
    busy, why = gpu_busy()
    if busy:
        print(f"U5 dispatch skipped: {why}")
    else:
        for req in data.get("requests", []):
            if req.get("status") != "retargeted":
                continue
            skill = (req.get("interpretation") or {}).get("skill_name", "unknown")
            terrain = (req.get("interpretation") or {}).get("needs_terrain")
            sup_skill = f"{skill}_auto"
            cmd = [sys.executable, SUPERVISOR, "--skill", sup_skill,
                   "--ref-json", req["ref_path"]] + TRAIN_ARGS
            # 地形が必要なスキルはU6実装後に--terrainを付与する(未実装時は保留)
            if terrain:
                print(f"U5 {req['id']}: {skill} は needs_terrain={terrain} — U6実装まで保留")
                continue
            if dry:
                print("U5 DRY-RUN:", " ".join(cmd))
            else:
                subprocess.Popen(cmd, cwd=HERE,
                                 creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                                 | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                                 stdout=open(os.path.join(r"C:\v50_work\autonomy",
                                                          f"supervisor_{sup_skill}_log.txt"), "w"),
                                 stderr=subprocess.STDOUT,
                                 env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                req["status"] = "training"
                req["training"] = {"supervisor_skill": sup_skill,
                                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
                changed += 1
                print(f"U5 dispatched {req['id']}: {skill} (supervisor skill={sup_skill})")
            break  # 1件のみ

    if changed and not dry:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print("U5 done")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    raise SystemExit(run_once(a.dry_run))
