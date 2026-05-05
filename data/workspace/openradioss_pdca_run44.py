"""OpenRadioss Run44 — engine-only restart from A030 (T=14.5ms).

Run43: NORMAL TERMINATION at T=14.88ms (3h, Eps_eff=0.22, TSTOP patched to 0.025s).
A031 exists from a pre-Run43 starter (incompatible model) → moved to backup before start.
Engine restarts automatically from the latest valid A-file (A030, T=14.5ms).
Target: 関門 T=0.01813s (+3.63ms, estimated ~45 min).
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
STATUS = ROOT / "data" / "workspace" / "openradioss_pdca_status.json"
CONTAINER = "clawstack-unified-openradioss-1"
ENGINE = "4mmx4mm_ASSY_20260105_0001.rad"
RUN_ID = "44"
THREADS = 4
CONFIG = ROOT / "data" / "state" / "openclaw.json"
WATCHDOG = ROOT / "data" / "workspace" / "openradioss_result_watchdog.py"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def write_status(payload: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def send_telegram(text: str) -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = cfg["channels"]["telegram"]["botToken"]
        chat_ids = [str(x) for x in cfg["channels"]["telegram"]["allowFrom"]]
        chat_id = "8173025084" if "8173025084" in chat_ids else chat_ids[0]
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            return f"sent:{res.status}"
    except Exception as exc:
        return f"failed:{exc}"


def main() -> None:
    if (ROOT / "data" / "workspace" / "openradioss_pdca_stop.flag").exists():
        raise RuntimeError("stop flag exists; not starting Run44")

    top = run(["docker", "top", CONTAINER]).stdout
    if "engine_linux64_gf" in top:
        raise RuntimeError("engine is already running; not starting Run44")

    # ── A031退避 (pre-Run43の不適合ファイル) ─────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run44_{ts}"
    run(["docker", "exec", CONTAINER, "bash", "-lc", f"mkdir -p {backup_dir}"])

    # A031が存在するか確認してから退避
    check_a031 = run(["docker", "exec", CONTAINER, "bash", "-lc",
                      "ls /work/4mmx4mm_ASSY_20260105A031 2>/dev/null"], check=False)
    a031_moved = False
    if check_a031.returncode == 0:
        run(["docker", "exec", CONTAINER, "bash", "-lc",
             f"mv /work/4mmx4mm_ASSY_20260105A031 {backup_dir}/"])
        a031_moved = True

    # ── _0001.rad バックアップ (エンジンカードは変更しない) ──────────
    run(["docker", "exec", CONTAINER, "bash", "-lc",
         f"cp /work/{ENGINE} {backup_dir}/"])

    # ── TSTOP確認 ────────────────────────────────────────────────────
    tstop_check = run(["docker", "exec", CONTAINER, "bash", "-lc",
                       f"head -5 /work/{ENGINE}"])
    tstop_line = [l for l in tstop_check.stdout.splitlines() if "0.025" in l or "0.020" in l or "0.015" in l]

    # ── エンジン起動 (スターター不要 — A030から自動再開) ──────────────
    engine_cmd = (
        "cd /work && rm -f /work/engine.pid && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/engine_linux64_gf "
        f"-i {ENGINE} -nt {THREADS} > /work/engine_run{RUN_ID}.log 2>&1 & "
        "echo $! > /work/engine.pid && echo started:$!"
    )
    start = run(["docker", "exec", CONTAINER, "bash", "-lc", engine_cmd])

    time.sleep(3)
    pid_check = run(["docker", "exec", CONTAINER, "bash", "-lc",
                     "cat /work/engine.pid 2>/dev/null"], check=False)
    pid = pid_check.stdout.strip()

    telegram_status = send_telegram(
        f"OpenRadioss Run44 開始\n"
        f"Run43: NORMAL TERM T=14.88ms (3h)\n"
        f"Run44: A030(T=14.5ms)から再開 → 関門T=18.13ms\n"
        f"推定残り~45分 / TSTOP=0.025s / Eps_eff=0.22\n"
        f"A031退避: {a031_moved}"
    )

    status = {
        "phase": "started",
        "run_id": RUN_ID,
        "container": CONTAINER,
        "restart_from": "A030 (T=14.5ms, Run43-generated)",
        "target": "関門 T=0.01813s (+3.63ms, ~45min)",
        "tstop": "0.025s (unchanged from Run43)",
        "eps_eff": "0.22 (set in Run43 starter, no re-run)",
        "a031_backup": f"{backup_dir}/4mmx4mm_ASSY_20260105A031" if a031_moved else "A031 not found",
        "tstop_line": tstop_line,
        "engine_pid": pid,
        "start_stdout": start.stdout.strip(),
        "telegram": telegram_status,
        "log": f"/work/engine_run{RUN_ID}.log",
        "next_check": f"docker exec {CONTAINER} tail -20 /work/engine_run{RUN_ID}.log",
    }
    write_status(status)
    print(json.dumps(status, ensure_ascii=False, indent=2))

    # ── Watchdog バックグラウンド起動 ────────────────────────────────
    import sys
    subprocess.Popen(
        [sys.executable, str(WATCHDOG), "--run-id", RUN_ID],
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )
    print(f"[run44] watchdog launched for Run{RUN_ID}")


if __name__ == "__main__":
    main()
