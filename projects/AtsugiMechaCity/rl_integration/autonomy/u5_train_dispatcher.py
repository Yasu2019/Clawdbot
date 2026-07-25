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


STALE_HOURS = 6.0  # T054 watchdog: 3000iterサイクル実績~3.3h。これを大きく超えるtraining状態はstale疑い
WORK_AUTONOMY = r"C:\v50_work\autonomy"
ESC_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\escalations"


def backfill_escalations():
    """C:\\v50_work(非バックアップ領域)の escalation.md をリポジトリ側へ回収(冪等)。
    2026-07-12導入: run_auto理由がC:にしか残らず消失しかけた再発防止。"""
    try:
        import glob as _glob
        os.makedirs(ESC_DIR, exist_ok=True)
        copied = 0
        for src in _glob.glob(os.path.join(WORK_AUTONOMY, "*", "escalation.md")):
            tag = os.path.basename(os.path.dirname(src))
            dst = os.path.join(ESC_DIR, f"recovered_{tag}.md")
            if os.path.exists(dst):
                continue
            with open(src, encoding="utf-8", errors="replace") as f:
                body = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(body)
            copied += 1
        if copied:
            print(f"U5 escalation backfill: {copied} file(s) recovered")
    except Exception as e:
        print("U5 escalation backfill skip:", e)


def trainer_alive():
    """学習系プロセスの生存確認。True/False、確認不能時は None(保守側で扱う)。"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                            "Where-Object { $_.CommandLine -match 'train_v50_walk_tracking|motion_learning_supervisor' } "
                            "| Measure-Object).Count"],
                           capture_output=True, text=True, timeout=60)
        return int((r.stdout or "0").strip() or 0) >= 1
    except Exception:
        return None


def status_age_hours(s):
    try:
        t = time.mktime(time.strptime(s.get("updated_at", ""), "%Y-%m-%dT%H:%M:%S"))
        return (time.time() - t) / 3600.0
    except Exception:
        return None


def stale_recovery(data):
    """T054 watchdog: state=進行系のままstale(>STALE_HOURS)かつプロセス死亡確定の
    場合のみ、2点セット復旧(supervisor_status→escalated / 依頼→retargeted)を自動実行。
    プロセス生存・確認不能・時刻解析不能のときは何もしない(誤リセット防止)。
    戻り値: 依頼側の変更件数。"""
    s = sup_state()
    if not (s and s.get("state") in ("running", "training", "checking")):
        return 0
    age = status_age_hours(s)
    if age is None or age <= STALE_HOURS:
        return 0
    alive = trainer_alive()
    if alive is not False:  # True(生存) or None(不明) → 触らない
        print(f"U5 watchdog: status stale {age:.1f}h but trainer alive={alive} — no action")
        return 0
    reason = (f"T054 watchdog auto-reset: state={s.get('state')} stale {age:.1f}h "
              f"(> {STALE_HOURS}h) and no trainer/supervisor process alive")
    print(f"U5 watchdog: {reason}")
    s["state"] = "escalated"
    s["escalation_reason"] = reason
    s["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(SUP_STATUS, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    changed = 0
    for req in data.get("requests", []):
        if req.get("status") == "training" and \
           (req.get("training") or {}).get("supervisor_skill") == s.get("skill"):
            req["status"] = "retargeted"
            req["watchdog_note"] = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {reason}"
            changed += 1
            print(f"U5 watchdog: {req['id']} training -> retargeted")
    return changed


def gpu_busy():
    """学習中判定: supervisorのstateが進行系、または学習系pythonプロセスが生存。"""
    s = sup_state()
    if s and s.get("state") in ("running", "training", "checking"):
        return True, f"supervisor busy: skill={s.get('skill')} state={s.get('state')}"
    if trainer_alive():
        return True, "trainer/supervisor process alive"
    return False, "idle"


def run_once(dry):
    if not os.path.exists(STORE):
        print("no queue file"); return 0
    data = json.load(open(STORE, encoding="utf-8"))
    changed = 0

    # (r) エスカレーション理由のリポジトリ側回収(冪等・非致命)
    backfill_escalations()

    # (t) Telegram outbox処理(2026-07-20導入・非致命。サンドボックス発の画像/テキスト送信)
    if not dry:
        try:
            from telegram_outbox import process_outbox
            process_outbox()
        except Exception as e:
            print("U5 outbox skip:", e)

    # (g) GPUプローブsentinel(2026-07-22・一回限り・read-only・非致命)。
    if not dry:
        gflag = os.path.join(HERE, "gpu_probe.flag")
        if os.path.exists(gflag):
            try:
                import gpu_probe
                gpu_probe.main()
            except Exception as e:
                print("U5 gpu_probe skip:", e)
            finally:
                try:
                    os.replace(gflag, gflag + ".done_" + time.strftime("%Y%m%d_%H%M%S"))
                except Exception:
                    pass

    # (r2) walk_auto クリーン再起動sentinel(2026-07-22・一回限り・非致命)。
    # 現行ランを止め、直後の sync/dispatch で新コード(n_envs4096+姿勢報酬)を再配車。
    if not dry:
        rflag = os.path.join(HERE, "restart_walk_auto.flag")
        if os.path.exists(rflag):
            try:
                import restart_walk_auto
                restart_walk_auto.main()
            except Exception as e:
                print("U5 restart_walk_auto skip:", e)
            finally:
                try:
                    os.replace(rflag, rflag + ".done_" + time.strftime("%Y%m%d_%H%M%S"))
                except Exception:
                    pass

    # (s) 旧ラン停止sentinel(2026-07-20・一回限り・非致命)。
    # stop_rogue.flag が存在する時のみ stop_rogue_walk を1回実行し、flagを.doneへ改名。
    # 再発火はflag再作成が必要=常時プロセス停止はしない(誤爆防止)。
    if not dry:
        flag = os.path.join(HERE, "stop_rogue.flag")
        if os.path.exists(flag):
            try:
                import stop_rogue_walk
                stop_rogue_walk.main()
            except Exception as e:
                print("U5 stop_rogue skip:", e)
            finally:
                try:
                    os.replace(flag, flag + ".done_" + time.strftime("%Y%m%d_%H%M%S"))
                except Exception:
                    pass

    # (w) T054 watchdog: 死んだsupervisorが残したstale進行状態を自動復旧
    if not dry:
        changed += stale_recovery(data)

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
