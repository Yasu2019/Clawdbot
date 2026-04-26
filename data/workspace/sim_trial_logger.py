"""
Simulation Trial Logger — ソルバー横断の試行結果をPostgreSQLに記録するユーティリティ。
対応ソルバー: openradioss, openfoam, elmer, abaqus, ansys 等
"""
import json
import sys
from datetime import datetime
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "sim_trials",
    "user": "postgres",
    "password": "change_me",
}


def _conn():
    return psycopg2.connect(**DB_CONFIG)


def log_trial(
    solver: str,
    analysis_type: str,
    run_number: int,
    model_file: str,
    parameters: dict,
    status: str = "running",
    results: dict | None = None,
    max_time_reached: float | None = None,
    failure_mode: str | None = None,
    notes: str | None = None,
    log_file: str | None = None,
) -> int:
    """試行を登録し、採番されたIDを返す。"""
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO simulation_trials
              (solver, analysis_type, run_number, model_file, parameters, results,
               max_time_reached, status, failure_mode, notes, log_file)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                solver, analysis_type, run_number, model_file,
                json.dumps(parameters, ensure_ascii=False),
                json.dumps(results, ensure_ascii=False) if results else None,
                max_time_reached, status, failure_mode, notes, log_file,
            ),
        )
        row_id = cur.fetchone()[0]
    print(f"[sim_trial_logger] registered id={row_id} run#{run_number} status={status}")
    return row_id


def update_trial(row_id: int, **kwargs):
    """試行結果を更新する（run終了時に呼ぶ）。"""
    allowed = {"results", "max_time_reached", "status", "failure_mode", "notes", "log_file"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    parts, vals = [], []
    for k, v in updates.items():
        if k in ("results",):
            parts.append(f"{k} = %s::jsonb")
            vals.append(json.dumps(v, ensure_ascii=False))
        else:
            parts.append(f"{k} = %s")
            vals.append(v)
    vals.append(row_id)
    with _conn() as con, con.cursor() as cur:
        cur.execute(f"UPDATE simulation_trials SET {', '.join(parts)} WHERE id = %s", vals)
    print(f"[sim_trial_logger] updated id={row_id} fields={list(updates.keys())}")


def query_similar(solver: str, analysis_type: str, top_n: int = 10):
    """同ソルバー・同解析種別の過去試行を新しい順に返す。"""
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            """
            SELECT id, run_number, run_date, status, max_time_reached,
                   failure_mode, parameters, results
            FROM simulation_trials
            WHERE solver=%s AND analysis_type=%s
            ORDER BY run_date DESC LIMIT %s
            """,
            (solver, analysis_type, top_n),
        )
        rows = cur.fetchall()
    return rows


def summary(solver: str | None = None):
    """全試行のサマリーを表示する。"""
    where = f"WHERE solver='{solver}'" if solver else ""
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            f"""
            SELECT solver, analysis_type, COUNT(*) AS runs,
                   SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS ok,
                   SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS ng,
                   MAX(max_time_reached) AS best_T
            FROM simulation_trials {where}
            GROUP BY solver, analysis_type
            ORDER BY solver, analysis_type
            """
        )
        rows = cur.fetchall()
    header = f"{'Solver':<15} {'Analysis':<30} {'Runs':>5} {'OK':>4} {'NG':>4} {'BestT':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        best = f"{r[5]:.4f}" if r[5] is not None else "—"
        print(f"{r[0]:<15} {r[1]:<30} {r[2]:>5} {r[3]:>4} {r[4]:>4} {best:>10}")


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        summary()
    elif cmd == "query":
        solver = sys.argv[2] if len(sys.argv) > 2 else "openradioss"
        atype  = sys.argv[3] if len(sys.argv) > 3 else "shear_blanking_4mmx4mm"
        rows = query_similar(solver, atype)
        for r in rows:
            print(r)
    else:
        print("Usage: sim_trial_logger.py [summary|query <solver> <analysis_type>]")
