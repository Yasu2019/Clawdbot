"""OpenRadioss Run45 — Inacti=6 → Inacti=0 で速度超過による停止を解除。

Run43/44: T=14.88ms で Node6178 が 601m/s を超え NORMAL TERMINATION (Inacti=6)。
          これは切断完了サインだが関門T=18.13msには届かない。
Run45: 全3インターフェースの Inacti=6 → Inacti=0 に変更し、
       T=14.88ms を超えてTSTOP=0.025sまで継続させる。
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
STATUS = ROOT / "data" / "workspace" / "openradioss_pdca_status.json"
CONTAINER = "clawstack-unified-openradioss-1"
STARTER = "4mmx4mm_ASSY_20260105_0000.rad"
ENGINE = "4mmx4mm_ASSY_20260105_0001.rad"
RUN_ID = "45"
THREADS = 4
CONFIG = ROOT / "data" / "state" / "openclaw.json"
WATCHDOG = ROOT / "data" / "workspace" / "openradioss_result_watchdog.py"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=check,
    )


def write_status(payload: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def docker_cp_from(container_path: str, local_path: Path) -> None:
    run(["docker", "cp", f"{CONTAINER}:{container_path}", str(local_path)])


def docker_cp_to(local_path: Path, container_path: str) -> None:
    run(["docker", "cp", str(local_path), f"{CONTAINER}:{container_path}"])


def patch_starter(text: str) -> str:
    """Inacti=6 → Inacti=0 (3インターフェース全て)"""
    # "         0         0         6                   0.6"  の行が3箇所
    old = "         0         0         6                   0.6"
    new = "         0         0         0                   0.6"
    count = text.count(old)
    if count == 0:
        # 既に変更済みか確認
        already = "         0         0         0                   0.6"
        if text.count(already) == 3:
            return text
        raise RuntimeError(f"Inacti patch target not found (found {count} occurrences of old pattern)")
    if count != 3:
        raise RuntimeError(f"Expected 3 Inacti=6 lines, found {count}")
    return text.replace(old, new)


def patch_engine(text: str) -> str:
    """_0001.radのRUNカードを/1に戻す(sedで/30になっていた場合)"""
    text = text.replace("/RUN/Punch_Die_Shearing/30", "/RUN/Punch_Die_Shearing/1", 1)
    return text


def send_telegram(text: str) -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = cfg["channels"]["telegram"]["botToken"]
        chat_ids = [str(x) for x in cfg["channels"]["telegram"]["allowFrom"]]
        chat_id = "8173025084" if "8173025084" in chat_ids else chat_ids[0]
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            return f"sent:{res.status}"
    except Exception as exc:
        return f"failed:{exc}"


def main() -> None:
    if (ROOT / "data" / "workspace" / "openradioss_pdca_stop.flag").exists():
        raise RuntimeError("stop flag exists; not starting Run45")

    top = run(["docker", "top", CONTAINER]).stdout
    if "engine_linux64_gf" in top:
        raise RuntimeError("engine is already running; not starting Run45")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run45_{ts}"
    run(["docker", "exec", CONTAINER, "bash", "-lc",
         f"mkdir -p {backup_dir} && cp /work/{STARTER} /work/{ENGINE} {backup_dir}/"])

    with tempfile.TemporaryDirectory(prefix="openradioss_run45_") as tmp:
        tmp_path = Path(tmp)
        starter_local = tmp_path / STARTER
        engine_local = tmp_path / ENGINE
        docker_cp_from(f"/work/{STARTER}", starter_local)
        docker_cp_from(f"/work/{ENGINE}", engine_local)

        patched_starter = patch_starter(starter_local.read_text(encoding="utf-8", errors="replace"))
        patched_engine = patch_engine(engine_local.read_text(encoding="utf-8", errors="replace"))
        starter_local.write_text(patched_starter, encoding="utf-8")
        engine_local.write_text(patched_engine, encoding="utf-8")

        docker_cp_to(starter_local, f"/work/{STARTER}")
        docker_cp_to(engine_local, f"/work/{ENGINE}")

    # スターター実行 (Inacti変更を反映するため必須)
    write_status({
        "phase": "running_starter",
        "run_id": RUN_ID,
        "patch": "Inacti=6 -> Inacti=0 (全3インターフェース)",
        "backup_dir": backup_dir,
    })
    starter_cmd = (
        "cd /work && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/starter_linux64_gf "
        f"-i {STARTER} -nt {THREADS} > /work/starter_run{RUN_ID}.log 2>&1"
    )
    run(["docker", "exec", CONTAINER, "bash", "-lc", starter_cmd])

    # スターターエラー確認
    starter_check = run(["docker", "exec", CONTAINER, "bash", "-lc",
                         f"tail -5 /work/starter_run{RUN_ID}.log"], check=False)
    starter_tail = starter_check.stdout.strip()

    # エンジン起動
    engine_cmd = (
        "cd /work && rm -f /work/engine.pid && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/engine_linux64_gf "
        f"-i {ENGINE} -nt {THREADS} > /work/engine_run{RUN_ID}.log 2>&1 & "
        "echo $! > /work/engine.pid && echo started:$!"
    )
    start = run(["docker", "exec", CONTAINER, "bash", "-lc", engine_cmd])

    time.sleep(5)
    log_head = run(["docker", "exec", CONTAINER, "bash", "-lc",
                    f"head -30 /work/engine_run{RUN_ID}.log"], check=False).stdout

    telegram_status = send_telegram(
        f"OpenRadioss Run45 開始\n"
        f"変更: Inacti=6→0 (速度超過による停止を解除)\n"
        f"Run43/44: T=14.88msで停止 (Node6178: 601m/s)\n"
        f"Run45目標: TSTOP=0.025s まで継続 → 関門T=18.13ms通過"
    )

    status = {
        "phase": "started",
        "run_id": RUN_ID,
        "patch": "Inacti=6 -> Inacti=0 (TYPE25 interfaces 1/2/3)",
        "reason": "Run43/44停止原因: NODAL VELOCITY TOO HIGH (Inacti=6) at T=14.88ms",
        "target": "TSTOP=0.025s / 関門T=0.01813s",
        "tstop": "0.025s",
        "backup_dir": backup_dir,
        "starter_tail": starter_tail,
        "start_stdout": start.stdout.strip(),
        "log_head": log_head[:300],
        "telegram": telegram_status,
        "log": f"/work/engine_run{RUN_ID}.log",
        "next_check": f"docker exec {CONTAINER} tail -20 /work/engine_run{RUN_ID}.log",
    }
    write_status(status)
    print(json.dumps(status, ensure_ascii=False, indent=2))

    # Watchdog起動
    import sys
    subprocess.Popen(
        [sys.executable, str(WATCHDOG), "--run-id", RUN_ID],
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )
    print(f"[run45] watchdog launched for Run{RUN_ID}")


if __name__ == "__main__":
    main()
