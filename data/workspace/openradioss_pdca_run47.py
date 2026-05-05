"""OpenRadioss Run47 — Run42の成功設定を復元 (Eps_eff=0.35, Inacti=6, VC=0.6, TSTOP=0.025s)

=== 根本原因分析 ===
Run42: Eps_eff=0.35, Inacti=6, VC=0.6, TSTOP=0.020s → T=19.992ms NORMAL TERM ✅ (関門18.13ms突破)
  Node6178最大速度=436m/s < VC=600m/s → WARNINGのみ、シミュレーション継続
Run43以降: Eps_eff=0.22に変更 → Node6178が601m/s(VC超過) → NORMAL TERM at T=14.88ms
Run45: Inacti=0に変更 → エネルギー崩壊ERR=-100% at T=13.1ms ABNORMAL TERM
Run46: Inacti=6,VC=5.0 (Eps_eff=0.22のまま) → Run45と同じエネルギー崩壊軌道 → 停止

=== Run47方針 ===
Eps_eff=0.35に戻す（Run42の証明済み設定）
Inacti=6, VC=0.6は変更なし
TSTOP=0.025s（Run42の0.020sより+5ms余裕）
→ T=19.99ms以上でNORMAL TERM(TSTOP到達)を期待
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
RUN_ID = "47"
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
    """全パラメータをRun42の成功設定に復元する。

    変更1: Inacti=0 → Inacti=6 (Run45/46パッチを元に戻す)
           または Inacti=6のまま → そのまま
    変更2: VC=5.0 → VC=0.6 (Run46パッチを元に戻す)
           または VC=0.6のまま → そのまま
    変更3: Eps_eff=0.22 → Eps_eff=0.35 (Run43で変更された根本原因を修正)
    """
    # Step1: Inacti を 6, VC を 0.6 に正規化
    # Run45後: Inacti=0, VC=0.6
    # Run46後: Inacti=6, VC=5.0
    # Run47目標: Inacti=6, VC=0.6
    for old, new in [
        ("         0         0         0                   0.6",
         "         0         0         6                   0.6"),
        ("         0         0         0                   5.0",
         "         0         0         6                   0.6"),
        ("         0         0         6                   5.0",
         "         0         0         6                   0.6"),
    ]:
        cnt = text.count(old)
        if cnt == 3:
            text = text.replace(old, new)
            break
        elif cnt > 0:
            text = text.replace(old, new)

    # Step2: Eps_eff=0.22 → 0.35 (GENE1 /FAIL カードの Eps_eff カラム)
    # 実際のファイル確認済み: "                0.22                 0.0" が一意に存在
    old_eps = "                0.22                 0.0"
    new_eps = "                0.35                 0.0"
    cnt_eps = text.count(old_eps)
    if cnt_eps == 0:
        # 既に0.35の場合
        if text.count(new_eps) > 0:
            pass  # 既にRun42設定
        else:
            raise RuntimeError(f"Eps_eff patch target not found (old={old_eps!r})")
    else:
        text = text.replace(old_eps, new_eps)

    return text


def patch_engine(text: str) -> str:
    """TSTOP=0.025s に設定 (Run42の0.020sより+5ms余裕)"""
    # TSTOP行: 2行目の数値
    # TSTOP: 0.020→0.025 または既に0.025なら何もしない
    text = text.replace("             0.0200000000", "             0.0250000000", 1)
    # /RUNカードの番号を1に戻す
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
        raise RuntimeError("stop flag exists; not starting Run47")

    top = run(["docker", "top", CONTAINER]).stdout
    if "engine_linux64_gf" in top:
        raise RuntimeError("engine is already running; not starting Run47")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/work/backup_run47_{ts}"
    run(["docker", "exec", CONTAINER, "bash", "-lc",
         f"mkdir -p {backup_dir} && cp /work/{STARTER} /work/{ENGINE} {backup_dir}/"])

    with tempfile.TemporaryDirectory(prefix="openradioss_run47_") as tmp:
        tmp_path = Path(tmp)
        starter_local = tmp_path / STARTER
        engine_local = tmp_path / ENGINE
        docker_cp_from(f"/work/{STARTER}", starter_local)
        docker_cp_from(f"/work/{ENGINE}", engine_local)

        orig_starter = starter_local.read_text(encoding="utf-8", errors="replace")
        orig_engine = engine_local.read_text(encoding="utf-8", errors="replace")

        # パッチ前後のEps_eff確認
        import re
        eps_before = re.findall(r'0\.\d{2}\s*\n', orig_starter[:5000])

        patched_starter = patch_starter(orig_starter)
        patched_engine = patch_engine(orig_engine)

        # パッチ確認
        if patched_starter.count("                0.35                 0.0") == 0:
            raise RuntimeError("Eps_eff=0.35 patch verification failed")
        if patched_starter.count("         0         0         6                   0.6") != 3:
            raise RuntimeError("Inacti=6 VC=0.6 patch verification failed")
        if "0.0250000000" not in patched_engine:
            raise RuntimeError("TSTOP=0.025 patch verification failed")

        starter_local.write_text(patched_starter, encoding="utf-8")
        engine_local.write_text(patched_engine, encoding="utf-8")

        docker_cp_to(starter_local, f"/work/{STARTER}")
        docker_cp_to(engine_local, f"/work/{ENGINE}")

    # スターター実行
    write_status({
        "phase": "running_starter",
        "run_id": RUN_ID,
        "patch": "Eps_eff=0.22→0.35 / Inacti=6 / VC=0.6 / TSTOP=0.025s",
        "rationale": "Run42(Eps_eff=0.35)がT=19.99msで成功。Run43でEps_eff=0.22に変更したことが全失敗の根本原因",
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
    if "ERROR" in starter_tail.upper() and "0 ERROR" not in starter_tail:
        raise RuntimeError(f"Starter errors detected: {starter_tail}")

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
        f"OpenRadioss Run47 開始\n"
        f"【根本原因修正】Eps_eff=0.22→0.35に戻す\n"
        f"Run42実績: Eps_eff=0.35でT=19.99ms成功(関門18.13ms突破)\n"
        f"Run43以降の全失敗原因: Eps_effを0.22に下げたこと\n"
        f"Run47: Inacti=6/VC=0.6/Eps_eff=0.35/TSTOP=0.025s\n"
        f"期待: Run42再現 → T≥19.99ms NORMAL TERMINATION"
    )

    status = {
        "phase": "started",
        "run_id": RUN_ID,
        "patch": "Eps_eff=0.22→0.35 / Inacti=6 / VC=0.6 / TSTOP=0.025s",
        "rationale": "Run42(Eps_eff=0.35,TSTOP=0.020s)→T=19.99ms成功。Run43でEps_eff=0.22に変更が根本原因",
        "reference_run": "Run42: T=19.992ms NORMAL TERM, Node6178=436m/s(<VC=600), Eps_eff=0.35",
        "target": "TSTOP=0.025s / 関門T=0.01813s",
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
    print(f"[run47] watchdog launched for Run{RUN_ID}")


if __name__ == "__main__":
    main()
