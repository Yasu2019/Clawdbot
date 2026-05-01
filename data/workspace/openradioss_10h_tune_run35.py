from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "backups" / "openradioss" / "run35_pre_10h_tuning_20260430"
WORK_DIR = ROOT / "data" / "workspace" / "openradioss_10h_tuning"
STATUS_PATH = ROOT / "data" / "workspace" / "openradioss_10h_tuning_status.json"

CONTAINER = "clawstack-unified-openradioss-1"
STARTER_NAME = "4mmx4mm_ASSY_20260105_0000.rad"
ENGINE_NAME = "4mmx4mm_ASSY_20260105_0001.rad"
RUN_ID = "37"

TARGET_TSTOP = "0.0014000000"
TARGET_DT = "0.80000E-07"
TARGET_DT_FLOAT = 8.0e-8
TARGET_ANIM_DT = "0.35000E-03"


def run(cmd: list[str], timeout: int = 60, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=check,
    )


def patch_engine_deck(src: Path, dst: Path) -> dict:
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    i = 0
    changes: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("/RUN/") and i + 1 < len(lines):
            out.append(line)
            out.append(f"             {TARGET_TSTOP}")
            changes.append(f"Tstop -> {TARGET_TSTOP} s")
            i += 2
            continue
        if stripped.startswith("/DT/NODA/CST") and i + 1 < len(lines):
            out.append(line)
            out.append(f"             0.90000             {TARGET_DT}")
            changes.append(f"minimum nodal timestep -> {TARGET_DT} s")
            i += 2
            continue
        if stripped.startswith("/RFILE") and i + 1 <= len(lines):
            out.append("/RFILE/50000")
            changes.append("restart/checkpoint interval -> 50000 cycles")
            i += 1
            continue
        if stripped.startswith("/ANIM/DT") and i + 1 < len(lines):
            out.append(line)
            out.append(f"             0.0000000000         {TARGET_ANIM_DT}")
            changes.append(f"animation output interval -> {TARGET_ANIM_DT} s")
            i += 2
            continue
        if stripped in {
            "/ANIM/ELEM/ENER",
            "/ANIM/ELEM/HOURG",
            "/ANIM/ELEM/SIGX",
            "/ANIM/ELEM/SIGY",
            "/ANIM/ELEM/SIGZ",
            "/ANIM/ELEM/SIGXY",
            "/ANIM/ELEM/SIGYZ",
            "/ANIM/ELEM/SIGZX",
            "/ANIM/VECT/VEL",
        }:
            changes.append(f"removed heavy output request {stripped}")
            i += 1
            continue
        out.append(line)
        i += 1
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {
        "target_tstop_sec": float(TARGET_TSTOP),
        "target_dt_sec": TARGET_DT_FLOAT,
        "estimated_cycles": int(float(TARGET_TSTOP) / TARGET_DT_FLOAT),
        "changes": changes,
    }


def write_status(payload: dict) -> None:
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Keep the current container inputs/logs before touching the active run.
    for name in [STARTER_NAME, ENGINE_NAME, "starter_run35.log", "engine_run35.log"]:
        run(["docker", "cp", f"{CONTAINER}:/work/{name}", str(BACKUP_DIR / name)], timeout=60, check=False)

    src_engine = BACKUP_DIR / ENGINE_NAME
    src_starter = BACKUP_DIR / STARTER_NAME
    tuned_engine = WORK_DIR / ENGINE_NAME
    tuned_starter = WORK_DIR / STARTER_NAME
    shutil.copy2(src_starter, tuned_starter)
    patch_info = patch_engine_deck(src_engine, tuned_engine)

    write_status(
        {
            "phase": "patched",
            "container": CONTAINER,
            "backup_dir": str(BACKUP_DIR),
            "work_dir": str(WORK_DIR),
            "patch": patch_info,
            "analysis": {
                "original_tstop_sec": 0.08,
                "original_dt_sec": 5.0e-8,
                "original_cycles": 1_600_000,
                "run35_observed": "T=0.00124 s after about 50,200 s elapsed; full run estimate was multi-week.",
                "tuning_basis": "About 17,500 cycles at the observed cycle rate is approximately 10 hours, while reducing the mass scaling seen with a 1.0e-7 s timestep.",
                "contact_notes": [
                    "Starter ended with 0 errors and 26 warnings.",
                    "Initial penetration warnings remain geometry/contact setup items; not silently changed in this timing-only run.",
                    "Heat exchange warnings are non-critical because thermal transfer is not active.",
                ],
            },
        }
    )

    run(["docker", "cp", str(tuned_starter), f"{CONTAINER}:/work/{STARTER_NAME}"], timeout=60)
    run(["docker", "cp", str(tuned_engine), f"{CONTAINER}:/work/{ENGINE_NAME}"], timeout=60)

    kill = run(["docker", "exec", CONTAINER, "bash", "/work/kill_engine.sh"], timeout=30, check=False)
    start = run(["docker", "exec", CONTAINER, "bash", "/work/start_engine.sh", RUN_ID], timeout=30, check=False)

    time.sleep(8)
    tail = run(["docker", "exec", CONTAINER, "tail", "-40", f"/work/engine_run{RUN_ID}.log"], timeout=30, check=False)
    pid = run(["docker", "exec", CONTAINER, "cat", "/work/engine.pid"], timeout=30, check=False)

    write_status(
        {
            "phase": "started",
            "container": CONTAINER,
            "run_id": RUN_ID,
            "backup_dir": str(BACKUP_DIR),
            "work_dir": str(WORK_DIR),
            "patch": patch_info,
            "kill_stdout": kill.stdout[-1000:],
            "start_stdout": start.stdout[-1000:],
            "engine_pid": pid.stdout.strip(),
            "engine_tail": tail.stdout[-3000:],
            "next_check": f"docker exec {CONTAINER} tail -80 /work/engine_run{RUN_ID}.log",
        }
    )
    print(STATUS_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
