"""OpenRadioss Run47 — Run42成功設定を rad_model で復元 (Eps=0.35, Inacti=6, VC=0.6, TSTOP=0.025s)."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "data" / "workspace"
WORK = ROOT / "clawstack_v2" / "data" / "work"
sys.path.insert(0, str(WS))

import rad_model as rm

STATUS = WS / "openradioss_pdca_status.json"
CONTAINER = "clawstack-unified-openradioss-1"
STARTER_NAME = "4mmx4mm_ASSY_20260105_0000.rad"
ENGINE_NAME = "4mmx4mm_ASSY_20260105_0001.rad"
STARTER = WORK / STARTER_NAME
ENGINE = WORK / ENGINE_NAME
RUN_ID = "47"
THREADS = 4
CONFIG = ROOT / "data" / "state" / "openclaw.json"
WATCHDOG = WS / "openradioss_result_watchdog.py"
GATE_MS = 18.13


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


def apply_run42_patch(starter: Path, engine: Path) -> dict:
    model = rm.RadModel(starter)
    model.set_fail_gene1(eps_eff=0.35).set_inter_type25_all(inacti=6, vc=0.6)
    model.write(starter)
    rm.set_engine_tstop(engine, 0.025)
    rm.set_engine_ams_scale(engine, 0.67)
    verify = model.verify()
    return verify


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


def parse_run_result(run_id: str) -> dict:
    import openradioss_hexmat_sweep as sw

    return sw.parse_engine_log(int(run_id))


def gate_pass(result: dict) -> bool:
    t = result.get("t_final_ms") or 0
    term = result.get("termination", "")
    return float(t) >= GATE_MS and term == "NORMAL_TSTOP"


def main() -> int:
    if (WS / "openradioss_pdca_stop.flag").exists():
        raise RuntimeError("stop flag exists; not starting Run47")

    top = run(["docker", "top", CONTAINER], check=False).stdout
    if "engine_linux64_gf" in top:
        run(["docker", "exec", CONTAINER, "bash", "-lc", "pkill -9 engine_linux 2>/dev/null; rm -f /work/engine.pid"], check=False)
        time.sleep(2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run47_{ts}"
    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "bash",
            "-lc",
            f"mkdir -p {backup_dir} && cp /work/{STARTER_NAME} /work/{ENGINE_NAME} {backup_dir}/",
        ]
    )

    verify = apply_run42_patch(STARTER, ENGINE)
    if float(verify.get("Eps_eff") or 0) != 0.35:
        raise RuntimeError(f"Eps_eff verify failed: {verify}")
    if int(verify.get("Inacti") or -1) != 6 or float(verify.get("VC") or 0) != 0.6:
        raise RuntimeError(f"Inacti/VC verify failed: {verify}")

    write_status(
        {
            "phase": "running_starter",
            "run_id": RUN_ID,
            "patch": "rad_model Eps=0.35 Inacti=6 VC=0.6 TSTOP=0.025 AMS=0.67",
            "verify": verify,
            "backup_dir": backup_dir,
        }
    )

    starter_cmd = (
        "cd /work && "
        "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
        "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
        f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/starter_linux64_gf "
        f"-i {STARTER_NAME} -nt {THREADS} > /work/starter_run{RUN_ID}.log 2>&1"
    )
    run(["docker", "exec", CONTAINER, "bash", "-lc", starter_cmd])
    err_line = run(
        ["docker", "exec", CONTAINER, "bash", "-lc", f"grep 'ERROR(S)' /work/{STARTER_NAME.replace('.rad', '.out')} | tail -1"],
        check=False,
    ).stdout
    if "0 ERROR(S)" not in err_line:
        raise RuntimeError(f"Starter failed: {err_line.strip()}")

    run(["docker", "exec", CONTAINER, "bash", "-c", f"bash /work/start_engine.sh {RUN_ID}"], check=False)
    time.sleep(3)

    telegram_status = send_telegram(
        "OpenRadioss Run47 開始 (rad_model patch)\n"
        "Eps=0.35 / Inacti=6 / VC=0.6 / TSTOP=0.025 / AMS=0.67\n"
        f"関門 T>={GATE_MS}ms NORMAL_TSTOP"
    )

    write_status(
        {
            "phase": "running_engine",
            "run_id": RUN_ID,
            "patch": "rad_model Run42 restore on production deck",
            "verify": verify,
            "backup_dir": backup_dir,
            "telegram": telegram_status,
            "log": f"/work/engine_run{RUN_ID}.log",
        }
    )

    import openradioss_hexmat_sweep as sw

    result = sw.wait_engine(int(RUN_ID))
    passed = gate_pass(result)
    status_payload = {
        "phase": "done",
        "run_id": RUN_ID,
        "result": result,
        "gate_passed": passed,
        "gate_ms": GATE_MS,
        "backup_dir": backup_dir,
    }
    write_status(status_payload)

    msg = (
        f"OpenRadioss Run47 {'PASS' if passed else 'FAIL'}\n"
        f"T={result.get('t_final_ms')}ms term={result.get('termination')}\n"
        f"gate>={GATE_MS}ms NORMAL_TSTOP: {'OK' if passed else 'NG'}"
    )
    send_telegram(msg)
    print(json.dumps(status_payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
