# -*- coding: utf-8 -*-
import re
import shlex
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync_base
from k10_lavie_exec_bridge import exec_host
import mf_of_calibration_db as cdb

JST = timezone(timedelta(hours=9))
OUT = Path(__file__).resolve().parent
RUN = "lavie-mfminusx-rfc-20260801-145637-r32"
BASE = f"/c/clawstack_satellite/data/work/cae_te_workspace/runs/{RUN}"
MF_PACK = OUT / "mf_minusx_copy_of_pack_20260801.json"


def run(cmd: str) -> str:
    try:
        result = sync_base.dispatch_shell("lavie", cmd, 60, sjp.load_token())
        stdout = result.get("stdout_tail") or ""
        stderr = result.get("stderr_tail") or ""
        if result.get("status") == "ok":
            return stdout or stderr
        if result.get("status") == "busy" or result.get("error") == "worker_busy":
            fallback = exec_host(
                "docker exec lavie-sjp-worker-c sh -lc " + shlex.quote(cmd),
                timeout=60,
            )
            fallback_stdout = fallback.get("stdout_tail") or ""
            fallback_stderr = fallback.get("stderr_tail") or ""
            if fallback.get("ok"):
                return fallback_stdout or fallback_stderr
            return (
                "ERR:fallback:"
                + str(fallback.get("exit_code"))
                + ":"
                + (fallback_stderr or fallback_stdout)
            )
        return f"ERR:{result.get('status')}:{result.get('error') or stderr or stdout}"
    except Exception as e:
        return f"ERR:{e}"


qbase = shlex.quote(BASE)
print("exists", run(f"test -f {qbase}/system/controlDict && echo YES"))
print("dir1", run(f"ls -1 {qbase} 2>/dev/null | head -80")[:1500])

# docker run to mount and read? too heavy
# Try type log via short path
for rel in (
    "log.interFoam",
    "interFoam.log",
    "foam.log",
    "solver.log",
):
    t = run(f"cat {qbase}/{shlex.quote(rel)} 2>/dev/null")
    print("file", rel, "len", len(t), "head", t[:80].replace("\n", " "))
    if "Phase-1" in t or "Time =" in t:
        (OUT / f"{RUN}_{rel}.txt").write_text(t[-20000:], encoding="utf-8", errors="replace")
        alphas = [float(x) for x in re.findall(r"Phase-1 volume fraction =\s*([0-9.eE+-]+)", t)]
        times = [float(x) for x in re.findall(r"Time =\s*([0-9.eE+-]+)", t)]
        print("alphas", len(alphas), "last", alphas[-1] if alphas else None)
        print("times last", times[-1] if times else None)

print("times", run(f"find {qbase} -maxdepth 1 -type d -printf '%f\\n' 2>/dev/null | head -80")[:1000])
print(
    "tail_log",
    run(
        f"tail -n 40 {qbase}/log.interFoam 2>/dev/null; "
        f"tail -n 40 {qbase}/interFoam.log 2>/dev/null"
    )[:2000],
)

# Also search jobs folder
print("jobs", run("ls -1 /c/clawstack_satellite/data/work/jobs 2>/dev/null | tail -80")[:800])
