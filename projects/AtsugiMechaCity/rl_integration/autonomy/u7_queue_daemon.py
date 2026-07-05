# -*- coding: utf-8 -*-
"""U7: キューオーケストレータ — skill_pipeline_implementation_spec.md 準拠。

5分ごとに skill_requests.json の状態を進める薄いポーリングループ:
  queued→U1解釈 / interpreted→U2お手本 / retarget_ready→U4リターゲット /
  retargeted・training→U5ディスパッチ&同期
各ユニットは --once のサブプロセスとして実行(1ユニット失敗が他を殺さない)。
keep_awake を保持し、状態を u7_status.json に書く。

usage: python u7_queue_daemon.py [--interval 300] [--once]
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = ["u1_interpreter.py", "u2_reference_finder.py",
         "u4_retarget_runner.py", "u5_train_dispatcher.py"]
STATUS = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\u7_status.json"


def run_units():
    results = {}
    for u in UNITS:
        try:
            r = subprocess.run([sys.executable, os.path.join(HERE, u), "--once"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=1800, cwd=HERE,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            tail = (r.stdout or "").strip().splitlines()
            results[u] = {"rc": r.returncode, "last": tail[-1] if tail else ""}
        except Exception as e:
            results[u] = {"rc": -1, "last": f"{type(e).__name__}: {e}"}
    return results


def write_status(results, cycles):
    os.makedirs(os.path.dirname(STATUS), exist_ok=True)
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"schema": "clawstack.u7_queue_daemon.v1",
                   "cycles": cycles, "units": results,
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
                  f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=300)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    try:
        from keep_awake import hold_awake
        hold_awake()
    except Exception:
        pass
    cycles = 0
    while True:
        cycles += 1
        results = run_units()
        write_status(results, cycles)
        for u, r in results.items():
            print(f"[U7 cycle {cycles}] {u}: rc={r['rc']} {r['last']}", flush=True)
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
