from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
STATUS = ROOT / "data" / "workspace" / "openradioss_pdca_status.json"
CONTAINER = "clawstack-unified-openradioss-1"
STARTER = "4mmx4mm_ASSY_20260105_0000.rad"
ENGINE = "4mmx4mm_ASSY_20260105_0001.rad"
RUN_ID = "42"
THREADS = 4
CONFIG = ROOT / "data" / "state" / "openclaw.json"


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


def docker_cp_from(container_path: str, local_path: Path) -> None:
    run(["docker", "cp", f"{CONTAINER}:{container_path}", str(local_path)])


def docker_cp_to(local_path: Path, container_path: str) -> None:
    run(["docker", "cp", str(local_path), f"{CONTAINER}:{container_path}"])


def patch_starter(text: str) -> str:
    old = "         0         0         6                   0.3"
    new = "         0         0         6                   0.6"
    count = text.count(old)
    if count == 0 and text.count(new) == 3:
        return text
    if count != 3:
        raise RuntimeError(f"expected 3 VISs lines at 0.3 or already 0.6, found {count}")
    return text.replace(old, new)


def patch_engine(text: str) -> str:
    old = "             0.0181300000"
    new = "             0.0200000000"
    if old not in text and new in text:
        return text
    if old not in text:
        raise RuntimeError("engine Tstop 0.0181300000 or 0.0200000000 not found")
    return text.replace(old, new, 1)


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
    status = {
        "phase": "preparing_run41",
        "container": CONTAINER,
        "run_id": RUN_ID,
        "mode": "bounded_pdca_single_run",
        "threads": THREADS,
        "stop_conditions": [
            "run42 reaches normal termination",
            "OpenRadioss terminates on fatal/error condition",
            "user creates data/workspace/openradioss_pdca_stop.flag before next run",
            "no automatic unlimited loop",
        ],
        "planned_patch": {
            "starter": "rerun starter so TYPE25 VISs=0.6 is actually reflected",
            "starter_VISs": "0.3 -> 0.6 for TYPE25 interfaces 1/2/3, if not already patched",
            "engine_Tstop_sec": "0.01813 -> 0.02000",
            "unchanged": ["Eps_eff=0.35", "Inacti=6", "DT/NODA/CST=1.2E-07"],
        },
    }
    write_status(status)

    top = run(["docker", "top", CONTAINER]).stdout
    if "engine_linux64_gf" in top:
        raise RuntimeError("engine is already running; not starting run41")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run41_{ts}"
    run(["docker", "exec", CONTAINER, "bash", "-lc", f"mkdir -p {backup_dir} && cp /work/{STARTER} /work/{ENGINE} {backup_dir}/"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        starter_local = tmp_path / STARTER
        engine_local = tmp_path / ENGINE
        docker_cp_from(f"/work/{STARTER}", starter_local)
        docker_cp_from(f"/work/{ENGINE}", engine_local)

        starter_text = starter_local.read_text(encoding="utf-8", errors="replace")
        engine_text = engine_local.read_text(encoding="utf-8", errors="replace")
        starter_local.write_text(patch_starter(starter_text), encoding="utf-8")
        engine_local.write_text(patch_engine(engine_text), encoding="utf-8")

        docker_cp_to(starter_local, f"/work/{STARTER}")
        docker_cp_to(engine_local, f"/work/{ENGINE}")

    run(["docker", "exec", CONTAINER, "bash", "/work/kill_engine.sh"])
    starter_cmd = (
        "cd /work && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/starter_linux64_gf "
        f"-i {STARTER} -nt {THREADS} > /work/starter_run{RUN_ID}.log 2>&1"
    )
    run(["docker", "exec", CONTAINER, "bash", "-lc", starter_cmd])
    engine_cmd = (
        "cd /work && rm -f /work/engine.pid && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/engine_linux64_gf "
        f"-i {ENGINE} -nt {THREADS} > /work/engine_run{RUN_ID}.log 2>&1 & "
        "echo $! > /work/engine.pid"
    )
    start = run(["docker", "exec", CONTAINER, "bash", "-lc", engine_cmd])
    telegram_status = send_telegram("Run41失敗のため、Run42を実行しました。")
    status.update(
        {
            "phase": "started",
            "backup_dir": backup_dir,
            "start_stdout": start.stdout,
            "telegram": telegram_status,
            "starter_log": f"/work/starter_run{RUN_ID}.log",
            "log": f"/work/engine_run{RUN_ID}.log",
            "next_check": f"docker exec {CONTAINER} tail -80 /work/engine_run{RUN_ID}.log",
        }
    )
    write_status(status)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
