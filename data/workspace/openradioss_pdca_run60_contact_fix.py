"""Run60: contact deck fix (Igap=2, Ishape=2, Irem=2, flip_skin) + NODA + physics verify."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
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
import openradioss_hexmat_sweep as sw
from openradioss_pdca_run56_58_59_sequence import (
    CONTAINER,
    CONFIG,
    DT_MIN,
    ENGINE,
    ENGINE_NAME,
    GATE_MS,
    RUN35_ENGINE,
    RUN35_STARTER,
    STARTER,
    STARTER_NAME,
    THREADS,
    docker_exec,
    engine_alive,
    kill_engine,
    run,
    send_telegram,
    wait_engine_until_exit,
)

RESULTS = WS / "openradioss_run60_results.jsonl"
STATUS = WS / "openradioss_pdca_status.json"
HEX_OUT = WORK / "4mmx4mm_ASSY_hexmat_run60_0000.rad"
ANIM_TO_VTK = "/opt/openradioss/OpenRadioss/exec/anim_to_vtk_linux64_gf"
PV = Path(r"C:\Program Files\ParaView 6.0.1\bin\pvpython.exe")


def build_hex_flip() -> None:
    cmd = [
        sys.executable,
        str(WS / "remesh_material_hex.py"),
        "--orig",
        str(RUN35_STARTER),
        "--out",
        str(HEX_OUT),
        "--isolid",
        "24",
        "--flip-skin",
    ]
    run(cmd)


def apply_deck() -> dict:
    build_hex_flip()
    shutil.copy2(HEX_OUT, STARTER)
    model = rm.RadModel(STARTER)
    model.set_fail_gene1(eps_eff=0.35)
    model.set_inter_type25_all(inacti=6, vc=0.6)
    model.set_inter_type25_contact(
        gap_max=0.1,
        stfac_punch=0.2,
        stfac_die=1e-4,
        stfac_strip=1e-4,
    )
    model.set_inter_type25_penetration_fix(igap=2, irem_i2=2, igap0=0, ishape=2)
    model.write(STARTER)
    return {
        "deck": model.verify(),
        "contact": {
            "Igap": 2,
            "Irem_i2": 2,
            "Igap0": 0,
            "Ishape": 2,
            "gap_max": 0.1,
            "flip_skin": True,
        },
    }


def apply_engine() -> dict:
    shutil.copy2(RUN35_ENGINE, ENGINE)
    rm.set_engine_tstop(ENGINE, 0.020)
    rm.set_engine_noda_dt_min(ENGINE, DT_MIN)
    return rm.read_engine_params(ENGINE)


def starter_ok(run_id: str) -> tuple[bool, str]:
    run(
        [
            "docker",
            "exec",
            CONTAINER,
            "bash",
            "-lc",
            (
                "cd /work && "
                "export LD_LIBRARY_PATH=/opt/openradioss/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH && "
                "export RAD_CFG_PATH=/opt/openradioss/OpenRadioss/hm_cfg_files && "
                f"OMP_NUM_THREADS={THREADS} /opt/openradioss/OpenRadioss/exec/starter_linux64_gf "
                f"-i {STARTER_NAME} -nt {THREADS} > /work/starter_run{run_id}.log 2>&1"
            ),
        ]
    )
    err = docker_exec(f"grep 'ERROR(S)' /work/{STARTER_NAME.replace('.rad', '.out')} | tail -1")
    pen = docker_exec(f"grep -c 'INITIAL PENETRATION' /work/starter_run{run_id}.log 2>/dev/null || echo 0")
    return "0 ERROR(S)" in err, f"errors={err.strip()} penetrations={pen.strip()}"


def physics_check_anim(step: int = 10) -> dict:
    anim = f"4mmx4mm_ASSY_20260105A{step:03d}"
    raw = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-lc", f"{ANIM_TO_VTK} /work/{anim}"],
        capture_output=True,
    )
    if raw.returncode != 0 or len(raw.stdout) < 5000:
        return {"ok": False, "reason": f"vtk convert fail rc={raw.returncode}"}
    vtk = WS / "run60_check.vtk"
    vtk.write_bytes(raw.stdout)
    code = f"""
import json as _json
from paraview.simple import LegacyVTKReader
import numpy as np
from pathlib import Path
r = LegacyVTKReader(FileNames=[{str(vtk.resolve())!r}])
r.UpdatePipeline()
out = r.GetClientSideObject().GetOutput()
cd = out.GetCellData()
part = np.array(cd.GetArray('PART_ID'))
v3 = np.array(cd.GetArray('3DELEM_Von_Mises'))
d = np.array(out.GetPointData().GetArray('Displacement'))
m2 = part == 2
vm = float(np.nanmax(v3[m2])) if m2.any() else 0.0
pt_ids = set()
for cid in np.where(m2)[0]:
    cell = out.GetCell(int(cid))
    for i in range(cell.GetNumberOfPoints()):
        pt_ids.add(cell.GetPointId(i))
pt_ids = sorted(pt_ids)
dm2 = 0.0
if d is not None and pt_ids:
    dm2 = float(np.linalg.norm(d[pt_ids], axis=1).max()) * 1000.0
dm = float(np.linalg.norm(d, axis=1).max()) * 1000.0 if d is not None else 0.0
print(_json.dumps({{"part2_von_mises_mpa": vm, "part2_disp_max_mm": dm2, "disp_max_mm": dm}}))
"""
    proc = subprocess.run([str(PV), "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return {"ok": False, "reason": (proc.stderr or proc.stdout)[-200:]}
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")][-1]
    stats = json.loads(line)
    stats["ok"] = stats.get("part2_von_mises_mpa", 0) > 1.0 and stats.get("part2_disp_max_mm", 0) > 0.05
    return stats


def main() -> int:
    kill_engine()
    verify = apply_deck()
    send_telegram("Run60 開始\ncontact fix: Igap=2 Ishape=2 flip_skin gap=0.1")

    ok, msg = starter_ok("60")
    verify["starter"] = msg
    if not ok:
        send_telegram(f"Run60 starter FAIL\n{msg}")
        raise SystemExit(f"starter failed: {msg}")

    verify["engine"] = apply_engine()
    run(["docker", "exec", CONTAINER, "bash", "-c", "bash /work/start_engine.sh 60"], check=False)
    time.sleep(3)
    result = wait_engine_until_exit("60")

    phys = physics_check_anim(10)
    passed = (
        float(result.get("t_final_ms") or 0) >= GATE_MS
        and result.get("termination") == "NORMAL_TSTOP"
        and phys.get("part2_von_mises_mpa", 0) > 1.0
        and phys.get("part2_disp_max_mm", 0) > 0.05
    )

    record = {
        "run_id": "60",
        "label": "HEX flip_skin + TYPE25 contact fix + NODA",
        "result": result,
        "physics_check_A010": phys,
        "gate_passed": passed,
        "verify": verify,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    STATUS.write_text(json.dumps({"phase": "run60", **record}, ensure_ascii=False, indent=2), encoding="utf-8")
    send_telegram(
        f"Run60 {'PASS' if passed else 'FAIL'}\n"
        f"T={result.get('t_final_ms')}ms {result.get('termination')}\n"
        f"PART2 stress={phys.get('part2_von_mises_mpa')}MPa disp={phys.get('disp_max_mm')}mm"
    )
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
