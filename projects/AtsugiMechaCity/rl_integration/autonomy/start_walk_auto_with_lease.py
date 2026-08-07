# -*- coding: utf-8 -*-
"""walk_auto の学習を GPUリースを確保してから起動するランチャー。2026-08-08 導入。

背景(実測):
- 2026-07-30 の学習は iteration 120/1500 で rc=4294967295 クラッシュし、
  train_stderr.log は空だった。前後にHunyuan3D/ComfyUIのGPU作業が重なっており、
  VRAM競合が疑われる(trouble_history: 他のGPU利用プロセスで bad allocation)。
- ComfyUIは生成後もVRAMを保持し続けるが、リースは解放済みのことがある。
  その状態は gpu_arbiter から「保持者なし」に見えるため、リース取得だけでは足りない。
  そこで起動前に実VRAM空きを確認し、不足していれば ComfyUI に /free を要求する。

安全設計:
- リースは priority=0 / nonpreemptible。学習中に他ジョブへ横取りされない。
- リースはこのランチャーのPIDに紐づけ、TTLを定期更新する。異常終了時は
  PID死活で自動回収される(ゾンビリース対策)。
- 子プロセスの stdout/stderr を必ずファイルへ分離記録する(前回stderrが空で
  クラッシュ原因を失った反省)。
- 既存の学習プロセスが居る場合は起動しない(二重起動防止)。

usage:
  python start_walk_auto_with_lease.py                     # n_envs=2048 で起動
  python start_walk_auto_with_lease.py --n-envs 4096 --iterations 3000
  python start_walk_auto_with_lease.py --dry-run
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\Clawdbot_Docker_20260125"
MECHA = os.path.join(REPO, "data", "workspace", "apps", "mecha_motion_lab")
SUPERVISOR = os.path.join(HERE, "motion_learning_supervisor.py")
LOG_DIR = r"C:\v50_work\autonomy"
DEFAULT_REF = r"C:\v50_work\refs\walk.json"
# motion_learning_supervisor は PY = sys.executable でトレーナーを起動するため、
# 監督自体を genesis 入りのvenvで動かさないと ModuleNotFoundError: genesis になる
# (2026-08-08 実測。システムPythonで起動して即失敗した)。
GENESIS_PY = r"C:\v50_work\genesis_venv\Scripts\python.exe"

sys.path.insert(0, os.path.join(REPO, "scripts"))
import gpu_arbiter  # noqa: E402

OWNER = "rl_walk_auto"
LEASE_TTL_SEC = 4 * 3600
RENEW_EVERY_SEC = 900


def _log(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        os.makedirs(MECHA, exist_ok=True)
        with open(os.path.join(MECHA, "walk_auto_launcher_log.txt"), "a",
                  encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def trainer_running():
    """既存の学習/監督プロセスが居るか。列挙不能なら安全側で True。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match "
             "'train_v50_walk_tracking|motion_learning_supervisor' } "
             "| Measure-Object).Count"],
            capture_output=True, text=True, timeout=60)
        return int((r.stdout or "0").strip() or 0) >= 1
    except Exception as e:
        _log(f"プロセス列挙に失敗: {type(e).__name__}: {e} -> 安全側で起動しない")
        return True


def ensure_vram(min_free_mb, comfy_free_url):
    """実VRAM空きを確保する。リース未保持のままVRAMを掴んでいるプロセス対策。"""
    free, total = gpu_arbiter.gpu_memory()
    if free is None:
        _log("VRAM取得に失敗。判定できないため続行しない")
        return False
    _log(f"VRAM空き {free} MB / 全体 {total} MB (必要 {min_free_mb} MB)")
    if free >= min_free_mb:
        return True
    _log("VRAM不足。ComfyUIへ /free を要求します(プロセスは停止しない)")
    gpu_arbiter.yield_comfyui(comfy_free_url)
    free, _ = gpu_arbiter.gpu_memory()
    _log(f"要求後のVRAM空き: {free} MB")
    return free is not None and free >= min_free_mb


def renew_loop(stop_event):
    while not stop_event.wait(RENEW_EVERY_SEC):
        if gpu_arbiter.renew(OWNER, LEASE_TTL_SEC):
            _log("GPUリースを更新しました")
        else:
            _log("GPUリースの更新に失敗(他者が保持している可能性)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skill", default="walk_auto")
    p.add_argument("--ref-json", default=DEFAULT_REF)
    p.add_argument("--n-envs", type=int, default=2048)
    p.add_argument("--iterations", type=int, default=3000)
    p.add_argument("--entropy", type=float, default=0.002)
    p.add_argument("--init-log-std", type=float, default=-0.9)
    p.add_argument("--python", default=GENESIS_PY,
                   help="監督とトレーナーを動かすPython(genesisが入っていること)")
    p.add_argument("--min-free-vram-mb", type=int, default=9000)
    p.add_argument("--comfy-free-url", default=gpu_arbiter.DEFAULT_COMFY_FREE_URL)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if not os.path.exists(a.ref_json):
        _log(f"参照モーションが見つかりません: {a.ref_json}")
        return 3
    if not os.path.exists(a.python):
        _log(f"学習用Pythonが見つかりません: {a.python}")
        return 3
    # genesis が入っているか事前検査する。入っていないと監督は起動するが
    # トレーナーが即死し、原因がエスカレーション文にしか残らない。
    try:
        r = subprocess.run([a.python, "-c", "import genesis; print(genesis.__version__)"],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            _log(f"genesis を import できません: {a.python}\n{(r.stderr or '')[-500:]}")
            return 3
        _log(f"学習用Python: {a.python} (genesis {r.stdout.strip()})")
    except Exception as e:
        _log(f"genesis 検査に失敗: {type(e).__name__}: {e}")
        return 3
    if trainer_running():
        _log("既に学習/監督プロセスが動いています。二重起動を避けて終了します")
        return 4

    cmd = [a.python, SUPERVISOR, "--skill", a.skill,
           "--ref-json", a.ref_json,
           "--iterations", str(a.iterations),
           "--entropy", str(a.entropy),
           "--init-log-std", str(a.init_log_std)]
    env = dict(os.environ, MECHA_N_ENVS=str(a.n_envs), PYTHONIOENCODING="utf-8")

    if a.dry_run:
        _log("DRY-RUN: " + " ".join(cmd) + f"  (MECHA_N_ENVS={a.n_envs})")
        return 0

    if not ensure_vram(a.min_free_vram_mb, a.comfy_free_url):
        _log("VRAMを確保できませんでした。起動を中止します")
        return 5

    ok, holder = gpu_arbiter.acquire(
        OWNER, priority=gpu_arbiter.PRIORITY_LONG_JOB,
        est_vram_mb=a.min_free_vram_mb, ttl_sec=LEASE_TTL_SEC,
        preemptible=False, wait_sec=0.0,
        note=f"walk_auto n_envs={a.n_envs} iterations={a.iterations}")
    if not ok:
        _log(f"GPUリースを取得できません。現保持者="
             f"{holder.get('owner') if holder else '不明'}")
        return 6
    _log(f"GPUリース取得: owner={OWNER} 期限={holder['expires_at']}")

    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(LOG_DIR, f"supervisor_{a.skill}_{stamp}_stdout.log")
    err_path = os.path.join(LOG_DIR, f"supervisor_{a.skill}_{stamp}_stderr.log")
    stop_event = threading.Event()
    t = threading.Thread(target=renew_loop, args=(stop_event,), daemon=True)
    t.start()

    rc = None
    try:
        _log("起動: " + " ".join(cmd) + f"  (MECHA_N_ENVS={a.n_envs})")
        _log(f"stdout={out_path}")
        _log(f"stderr={err_path}")
        with open(out_path, "w", encoding="utf-8") as fo, \
                open(err_path, "w", encoding="utf-8") as fe:
            proc = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=fo, stderr=fe)
            _log(f"supervisor pid={proc.pid}")
            rc = proc.wait()
    except KeyboardInterrupt:
        _log("中断されました")
    finally:
        stop_event.set()
        gpu_arbiter.release(OWNER)
        _log(f"GPUリースを解放しました (supervisor rc={rc})")

    if rc not in (0, None):
        _log(f"supervisor が異常終了しました rc={rc}。stderr を確認してください: {err_path}")
        try:
            tail = open(err_path, encoding="utf-8", errors="replace").read()[-1500:]
            if tail.strip():
                _log("stderr tail:\n" + tail)
            else:
                _log("stderr は空でした(子プロセス側のクラッシュはOS由来の可能性)")
        except Exception:
            pass
    return 0 if rc in (0, None) else 7


if __name__ == "__main__":
    raise SystemExit(main())
