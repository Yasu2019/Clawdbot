# -*- coding: utf-8 -*-
"""Register the fail-closed INC-188 Trial T learning record."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "workspace" / "universal_growth.db"
CHALLENGE = "INC-188 Trial T stripper hold causality and global rupture"


def main() -> int:
    know_how = (
        "Goal: isolate stripper overtravel in four-part blanking. Context: 4x4x0.5 mm "
        "AA1060-labelled blank, 2000 BRICK, SPM80, natural DT. Observed: the old "
        "0.190 mm target exceeded the 0.100 mm gap; Trial T held at 0.099 mm, Starter "
        "0 errors/warnings, TSTOP 3.7902 ms in 1508.54 s, DT 7.7145 ns, DM/M 0, "
        "ERR -84.7%, rupture 1946/2000. Hypothesis rejected: overtravel alone caused "
        "global rupture. Decision rule: IF target >= gap THEN reject; IF rupture >50% "
        "or energy gate fails THEN exclude from PINN regardless of TSTOP. Procedure: "
        "validate gap, plateau stripper, run one-variable trial, audit unique rupture "
        "IDs and ERR. Verification: five tests pass; Trial T physical FAIL. Recovery: "
        "backup/inc188-before-stripper-hold-20260810. Scope: no material calibration "
        "or commercial validation. Next: known AA1060 temper plus measured coupon or "
        "blanking force-stroke calibration. Provenance: INC-188, 2026-08-10, Trial T."
    )
    evidence = (
        '{"trial":"T","tstop_s":0.0037902,"runtime_s":1508.54,'
        '"dt_s":7.7145e-9,"dm_m":0.0,"energy_error_pct":-84.7,'
        '"rupture_unique":1946,"material_elements":2000,'
        '"verdict":"FAILED_PHYSICAL_GLOBAL_RUPTURE","tests_passed":5}'
    )
    connection = sqlite3.connect(DB, timeout=60)
    connection.execute("PRAGMA busy_timeout=60000")
    exists = connection.execute(
        "SELECT id FROM growth_records WHERE domain=? AND challenge=?",
        ("OPENRADIOSS_BLANKING", CHALLENGE),
    ).fetchone()
    if exists:
        print(f"[SKIP] growth_records id={exists[0]}")
    else:
        cursor = connection.execute(
            "INSERT INTO growth_records "
            "(domain, challenge, status, know_how, artifact_path, difficulty, evidence, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "OPENRADIOSS_BLANKING", CHALLENGE, "FAILED", know_how,
                "docs/quality_incident_report_20260810_shear_mesh_explosion_inc188.md",
                5, evidence,
                "local_solver:INC188T; web:Altair_official+MakeItFrom_secondary",
            ),
        )
        connection.commit()
        print(f"[OK] growth_records id={cursor.lastrowid}")
    bad = connection.execute(
        "SELECT COUNT(*) FROM growth_records WHERE challenge=? AND "
        "(know_how LIKE ? OR evidence LIKE ?)",
        (CHALLENGE, "%\ufffd%", "%\ufffd%"),
    ).fetchone()[0]
    connection.close()
    if bad:
        raise ValueError("replacement character found in Trial T DB record")
    print("[OK] replacement_character_rows=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
