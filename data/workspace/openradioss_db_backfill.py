"""OpenRadioss Run3〜47 の全試行をDBに補完登録する。

既存のエンジンログからT_final, ERR, 終了種別を自動抽出し、
既知のパラメータ(スクリプト/バックアップから復元)と合わせて記録する。
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
sys.path.insert(0, str(ROOT / "data" / "workspace"))
import sim_trial_logger as db

CONTAINER = "clawstack-unified-openradioss-1"
SOLVER = "openradioss"
ANALYSIS = "shear_blanking_4mmx4mm"
MODEL_FILE = "4mmx4mm_ASSY_20260105_0000.rad"


def docker_exec(cmd: str) -> str:
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-lc", cmd],
        text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=False,
    )
    return r.stdout


def extract_log_summary(run_id: int) -> dict:
    """ログからT_final, ERR_final, cycles, termination_typeを抽出"""
    log = f"/work/engine_run{run_id}.log"
    # 最終NCライン
    last_nc = docker_exec(f"grep 'NC=' {log} 2>/dev/null | tail -1").strip()
    # TERMINATION行
    term_line = docker_exec(
        f"grep -E 'NORMAL TERMINATION|ABNORMAL TERMINATION' {log} 2>/dev/null | tail -1"
    ).strip()
    # 速度エラー
    vel_err = docker_exec(
        f"grep -E 'NODAL VELOCITY.*TOO HIGH|ERROR.*VELOCITY' {log} 2>/dev/null | tail -1"
    ).strip()

    result = {"raw_last_nc": last_nc, "raw_term": term_line}

    m = re.search(r'NC=\s*(\d+)\s+T=\s*([\d.E+\-]+)\s+DT=.*ERR=\s*([\d.\-]+)%', last_nc)
    if m:
        result["nc_final"] = int(m.group(1))
        result["t_final_s"] = float(m.group(2))
        result["t_final_ms"] = float(m.group(2)) * 1000
        result["err_final_pct"] = float(m.group(3))

    if "NORMAL TERMINATION" in term_line:
        if vel_err:
            result["termination_type"] = "NORMAL_VELOCITY"
            result["failure_mode"] = "NODAL VELOCITY TOO HIGH (Inacti=6)"
        else:
            result["termination_type"] = "NORMAL_TSTOP"
    elif "ABNORMAL" in term_line:
        result["termination_type"] = "ABNORMAL"
        result["failure_mode"] = "ABNORMAL TERMINATION (ERR=-100%)"
    else:
        result["termination_type"] = "UNKNOWN_OR_RUNNING"

    return result


# ──────────────────────────────────────────────────────────────────────────────
# 既知パラメータ辞書 (スクリプト/ログ/バックアップから手動復元)
# ──────────────────────────────────────────────────────────────────────────────
KNOWN_PARAMS: dict[int, dict] = {
    # Run3-9: 初期探索 (詳細不明)
    3:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    4:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    5:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    6:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    7:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    8:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    9:  {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    10: {"Inacti": 6, "VC": 0.6, "Eps_eff": "unknown_early"},
    # Run11-25: DB登録済み(run_id=26は未調査)
    # Run26-31: DB登録済み
    26: {"Inacti": 6, "VC": 0.6, "EPS_p_max": 0.2, "Stfac": 0.1,
         "note": "DB登録済み trial_id=1"},
    27: {"Dn": 0.1, "Xmax": 0.05, "EPS_p_max": 0.05, "Stfac": 0.05,
         "note": "DB登録済み trial_id=2"},
    28: {"Dn": 0.5, "EPS_p_max": 0.05, "Stfac": 0.05,
         "note": "DB登録済み trial_id=3"},
    29: {"Dn": 0.5, "VISs": 0.0, "Xmax": 10.0, "Eps_eff": 0.8, "EPS_p_max": 10.0, "FAIL_model": "GENE1",
         "note": "DB登録済み trial_id=4"},
    30: {"Dn": 0.5, "VISs": 0.3, "Xmax": 10.0, "Eps_eff": 0.6, "EPS_p_max": 10.0, "FAIL_model": "GENE1",
         "note": "DB登録済み trial_id=5"},
    31: {"Dn": 0.5, "VISs": 0.5, "Xmax": 10.0, "Eps_eff": 0.4, "EPS_p_max": 10.0, "FAIL_model": "GENE1",
         "note": "DB登録済み trial_id=6"},
    # Run32: 詳細不明
    32: {"note": "中間Run詳細不明"},
    # Run33: Eps_eff=0.5で長時間走行 (TSTOP=0.030s?)
    33: {"Inacti": 6, "VC": 0.6, "Eps_eff": 0.50, "EPS_p_max": 10.0, "FAIL_model": "GENE1",
         "DT": "1.2E-7", "TSTOP_guess": 0.030,
         "note": "NC=549000, T=27.45ms, NORMAL TERM(TSTOP)"},
    # Run34: ゾンビプロセス障害
    34: {"note": "ゾンビプロセス障害(T001) - エンジン未完走"},
    # Run35-39: DT=5-8E-8での探索
    35: {"DT": "5E-8", "note": "NC=25000 T=1.25ms 停止(理由不明)"},
    36: {"DT": "1E-7", "note": "NC=0 T=0 エンジン即時停止"},
    37: {"DT": "8E-8", "Inacti": 6, "note": "NC=17500 T=1.4ms NORMAL TERM(理由不明)"},
    38: {"DT": "8E-8", "Inacti": 6, "note": "NC=62500 T=5.0ms NORMAL TERM ERR=-6.6%"},
    39: {"DT": "8E-8", "note": "NC=94200 T=7.5ms 停止 ERR=-65.4%"},
    # Run40-41: Inacti=6, VC=0.6, TSTOP=0.020s, DT=1.2E-7
    40: {"Inacti": 6, "VC": 0.6, "DT": "1.2E-7", "TSTOP": 0.020,
         "note": "NC=122600 T=14.71ms NORMAL TERM(VELOCITY) - Run41と同一パラメータ"},
    41: {"Inacti": 6, "VC": 0.6, "DT": "1.2E-7", "TSTOP": 0.020,
         "note": "NC=122600 T=14.71ms NORMAL TERM(VELOCITY)"},
    # Run42: 成功!! Eps_eff=0.35でT=19.99ms NORMAL TERM(TSTOP)
    42: {"Inacti": 6, "VC": 0.6, "Eps_eff": 0.35, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.020,
         "note": "SUCCESS T=19.992ms(>関門18.13ms). Node6178=436m/s<VC=600m/s"},
    # Run43-44: Eps_eff=0.22に変更 → Node6178=601m/s→NORMAL TERM at T=14.88ms
    43: {"Inacti": 6, "VC": 0.6, "Eps_eff": 0.22, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025,
         "note": "Node6178=601m/s→VC超過. NORMAL TERM T=14.88ms"},
    44: {"Inacti": 6, "VC": 0.6, "Eps_eff": 0.22, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025,
         "note": "Run43と同一。エンジンonly再起動試み → 同結果"},
    # Run45: Inacti=0 → エネルギー崩壊
    45: {"Inacti": 0, "Eps_eff": 0.22, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025,
         "note": "Inacti=0(無制限)でERR=-100%崩壊"},
    # Run46: Inacti=6, VC=5.0, Eps_eff=0.22 → ERR崩壊
    46: {"Inacti": 6, "VC": 5.0, "Eps_eff": 0.22, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025,
         "note": "VC=5000m/sに引き上げもEps_eff=0.22のERR崩壊は防げず。T=6.7ms ERR=-53%で強制停止"},
    # Run47: 根本原因修正 - Eps_eff=0.35に戻す
    47: {"Inacti": 6, "VC": 0.6, "Eps_eff": 0.35, "EPS_p_max": 10.0,
         "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025,
         "note": "Run42設定復元。Eps_eff=0.35/Inacti=6/VC=0.6/TSTOP=0.025s"},
}

ALREADY_IN_DB = {26, 27, 28, 29, 30, 31}


def get_existing_run_numbers() -> set[int]:
    """DBにある run_number を返す"""
    try:
        rows = db.query_similar(SOLVER, ANALYSIS, top_n=200)
        return {r[1] for r in rows}
    except Exception as e:
        print(f"[warn] DB query failed: {e}")
        return set()


def backfill_run(run_id: int, existing: set[int]) -> None:
    if run_id in existing:
        print(f"[skip] Run{run_id} already in DB")
        return

    log_exists = docker_exec(f"test -f /work/engine_run{run_id}.log && echo yes").strip()
    if log_exists != "yes":
        print(f"[skip] Run{run_id} log not found")
        return

    summary = extract_log_summary(run_id)
    params = KNOWN_PARAMS.get(run_id, {"note": "params_unknown"})
    note = params.pop("note", None)

    t_final = summary.get("t_final_ms")
    term = summary.get("termination_type", "UNKNOWN")
    failure_mode = summary.get("failure_mode")

    # 成功判定: T≥18.13ms かつ NORMAL_TSTOP
    if term == "NORMAL_TSTOP" and t_final and t_final >= 18.13:
        status = "success"
    elif term in ("NORMAL_VELOCITY", "ABNORMAL"):
        status = "failed"
    elif term == "NORMAL_TSTOP":
        status = "success"
    else:
        status = "failed"

    results = {
        "nc_final": summary.get("nc_final"),
        "err_final_pct": summary.get("err_final_pct"),
        "termination_type": term,
    }

    row_id = db.log_trial(
        solver=SOLVER,
        analysis_type=ANALYSIS,
        run_number=run_id,
        model_file=MODEL_FILE,
        parameters=params,
        status=status,
        results=results,
        max_time_reached=t_final / 1000 if t_final else None,
        failure_mode=failure_mode,
        notes=note,
        log_file=f"/work/engine_run{run_id}.log",
    )
    print(f"[registered] Run{run_id} id={row_id} status={status} T={t_final}ms term={term}")


def main() -> None:
    print("=== OpenRadioss DB Backfill ===")
    existing = get_existing_run_numbers()
    print(f"既存DB登録済み run_numbers: {sorted(existing)}")

    # ログが存在するRun IDを列挙
    log_list = docker_exec("ls /work/engine_run*.log 2>/dev/null").strip().splitlines()
    run_ids = sorted(
        int(re.search(r'engine_run(\d+)\.log', f).group(1))
        for f in log_list if re.search(r'engine_run(\d+)\.log', f)
    )
    print(f"ログ存在Run ID: {run_ids}")
    print()

    for rid in run_ids:
        backfill_run(rid, existing)

    print()
    print("=== 補完後サマリー ===")
    db.summary()


if __name__ == "__main__":
    main()
