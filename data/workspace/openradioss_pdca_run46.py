"""OpenRadioss Run46 — Inacti=6 (維持) + VC=0.6 → 5.0 で速度閾値を引き上げ。

Run45: Inacti=0 に変更 → ERR=-99.9% でエネルギー崩壊 (T=13.1ms, ABNORMAL TERM)
原因: VC=0.6 (600m/s) の閾値がわずか1m/s低すぎ Node6178=601m/s → NORMAL TERM (Run43/44)
      Inacti=0 は無制限 → 切断後の飛散片がコンタクト拘束を破壊 → エネルギー崩壊

Run46: Inacti=6 を維持 (安全弁として機能) + VC=0.6→5.0 (5000m/s) に引き上げ
       切断後の飛散片(~600m/s)は閾値未満 → NORMAL TERMを回避してTSTOP=0.025sまで継続
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
RUN_ID = "46"
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
    """Inacti=0,VC=0.6 → Inacti=6,VC=5.0 (TYPE25 全3インターフェース)

    Run45で Inacti=6→0 に変えた。Run46では:
      - Inacti=6 に戻す (安全弁)
      - VC=0.6 (600m/s) → 5.0 (5000m/s) に引き上げ
    """
    old = "         0         0         0                   0.6"
    new = "         0         0         6                   5.0"
    count = text.count(old)
    if count == 0:
        # 既にRun46パッチ済みか確認
        if text.count(new) == 3:
            return text
        # Inacti=6,VC=0.6 (Run43/44 初期状態) から直接パッチする場合
        old_orig = "         0         0         6                   0.6"
        count_orig = text.count(old_orig)
        if count_orig == 3:
            return text.replace(old_orig, new)
        raise RuntimeError(
            f"patch target not found: Inacti=0,VC=0.6 ({count}件) / Inacti=6,VC=0.6 ({count_orig}件)"
        )
    if count != 3:
        raise RuntimeError(f"Expected 3 patch target lines, found {count}")
    return text.replace(old, new)


def patch_engine(text: str) -> str:
    """/RUN カードが /30 になっていた場合 /1 に戻す"""
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
        raise RuntimeError("stop flag exists; not starting Run46")

    top = run(["docker", "top", CONTAINER]).stdout
    if "engine_linux64_gf" in top:
        raise RuntimeError("engine is already running; not starting Run46")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run46_{ts}"
    run(["docker", "exec", CONTAINER, "bash", "-lc",
         f"mkdir -p {backup_dir} && cp /work/{STARTER} /work/{ENGINE} {backup_dir}/"])

    with tempfile.TemporaryDirectory(prefix="openradioss_run46_") as tmp:
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

    # スターター実行
    write_status({
        "phase": "running_starter",
        "run_id": RUN_ID,
        "patch": "Inacti=6 (維持) + VC=0.6→5.0 (速度閾値5000m/sへ引き上げ)",
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
        f"OpenRadioss Run46 開始\n"
        f"変更: Inacti=6維持 + VC=0.6→5.0 (速度閾値600m/s→5000m/s)\n"
        f"Run45失敗: Inacti=0 → ERR=-100% (T=13.1ms)\n"
        f"Run45/44: VC=0.6 (600m/s) がNode6178 (601m/s) に対して1m/s低すぎた\n"
        f"Run46目標: TSTOP=0.025s / 関門T=18.13ms通過"
    )

    status = {
        "phase": "started",
        "run_id": RUN_ID,
        "patch": "Inacti=6 (維持) + VC=0.6→5.0",
        "reason": "Run45失敗: Inacti=0でERR=-100%(T=13.1ms) / Run43-44: VC=0.6(600m/s)が1m/s低すぎNode6178(601m/s)でNORMAL TERM",
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

    import sys
    subprocess.Popen(
        [sys.executable, str(WATCHDOG), "--run-id", RUN_ID],
        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
    )
    print(f"[run46] watchdog launched for Run{RUN_ID}")


if __name__ == "__main__":
    main()
