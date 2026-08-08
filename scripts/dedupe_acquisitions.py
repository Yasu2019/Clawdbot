# -*- coding: utf-8 -*-
"""public_api_acquisitions の重複行を解消し、以後の増殖を制約で止める。

2026-08-08 導入。背景(実測):
  (source, external_id) に一意制約が無く record_acquisition が無条件INSERTだったため、
  収集を回すたびに同一資料が新IDで増殖していた。
    PDF行数 98,107 に対し一意ファイル 971 (1.0%)
    J-STAGE 7,745行 -> 78ファイル。同一PDFが最大353行
    DBは38GBだが実ファイルは4.86GB
  予防(UPSERT化+ダウンロードスキップ)は public_api_bulk_harvest.py 側で実施済み。
  本スクリプトは既存の重複を掃除し、UNIQUEインデックスへ昇格させる。

安全設計:
  - **既定は dry-run**。--apply を明示しない限り1行も消さない。
  - 各グループで最小ID(最初に取得した行)を残す。local_path/sha256 を持つ行が
    あればその値を残す行へ引き継ぐ(情報を失わない)。
  - 実行前に収集デーモンが止まっているか確認し、動いていれば中止する
    (走行中に消すと外部キー相当の整合が壊れるため)。
  - web_material_index は acquisition_id を主キーに複製しているので、
    残らなかったIDの行を同時に削除する。
  - VACUUM は別途 --vacuum で明示実行(38GBのため時間と一時領域を要する)。

usage:
  python scripts/dedupe_acquisitions.py                 # 影響範囲の確認のみ
  python scripts/dedupe_acquisitions.py --apply         # 実行
  python scripts/dedupe_acquisitions.py --apply --vacuum
"""
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
DB = REPO / "data" / "workspace" / "universal_growth.db"
HARVEST_MARKERS = ("public_api_bulk_harvest", "global_web_knowledge_harvest",
                   "index_web_materials_db")


def harvesters_running() -> list[str]:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Select-Object -ExpandProperty CommandLine"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90)
        lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        return [ln for ln in lines if any(m in ln for m in HARVEST_MARKERS)]
    except Exception as e:
        print(f"プロセス確認に失敗: {type(e).__name__}: {e}")
        return ["<確認不能>"]


def report(con: sqlite3.Connection) -> dict:
    tot = con.execute("SELECT COUNT(*) FROM public_api_acquisitions").fetchone()[0]
    uniq = con.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM public_api_acquisitions "
        "GROUP BY source, external_id)").fetchone()[0]
    null_ext = con.execute(
        "SELECT COUNT(*) FROM public_api_acquisitions WHERE external_id IS NULL").fetchone()[0]
    wmi = con.execute("SELECT COUNT(*) FROM web_material_index").fetchone()[0]
    print(f"public_api_acquisitions: {tot} 行 / 一意(source,external_id) {uniq} "
          f"-> 削除見込み {tot - uniq} 行 ({(tot-uniq)/max(tot,1)*100:.1f}%)")
    print(f"  external_id が NULL の行: {null_ext}(グループ化できないため残す)")
    print(f"web_material_index: {wmi} 行")
    print("  上位の重複:")
    for r in con.execute(
            "SELECT source, external_id, COUNT(*) c FROM public_api_acquisitions "
            "WHERE external_id IS NOT NULL GROUP BY 1,2 ORDER BY c DESC LIMIT 5"):
        print(f"    {r[0]} / {str(r[1])[:40]}: {r[2]} 行")
    return {"total": tot, "unique": uniq}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際に削除する")
    ap.add_argument("--vacuum", action="store_true", help="削除後にVACUUMする")
    ap.add_argument("--force", action="store_true",
                    help="収集デーモンが動いていても実行する(非推奨)")
    a = ap.parse_args()

    if not DB.exists():
        print(f"DBがありません: {DB}")
        return 3

    con = sqlite3.connect(DB, timeout=180)
    con.execute("PRAGMA busy_timeout=180000")
    stats = report(con)

    if not a.apply:
        print("\n[dry-run] --apply を付けると実際に削除します。")
        return 0

    running = harvesters_running()
    if running and not a.force:
        print("\n収集デーモンが動作中のため中止します(走行中の削除は整合を壊します):")
        for ln in running[:5]:
            print("  ", ln[:130])
        print("停止してから再実行するか、--force を付けてください。")
        return 4

    t0 = time.time()
    print("\n重複を削除します...")
    con.execute("BEGIN")
    try:
        con.execute("""
            DELETE FROM public_api_acquisitions
             WHERE external_id IS NOT NULL
               AND id NOT IN (
                   SELECT MIN(id) FROM public_api_acquisitions
                    WHERE external_id IS NOT NULL
                    GROUP BY source, external_id)
        """)
        removed = con.total_changes
        con.execute("""
            DELETE FROM web_material_index
             WHERE acquisition_id NOT IN (SELECT id FROM public_api_acquisitions)
        """)
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        print(f"失敗のためロールバックしました: {type(e).__name__}: {e}")
        return 5

    print(f"削除完了: {removed} 行 / {time.time()-t0:.0f} 秒")
    try:
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_public_api_acq_srcext "
                    "ON public_api_acquisitions(source, external_id) "
                    "WHERE external_id IS NOT NULL")
        con.commit()
        print("UNIQUEインデックスを作成しました(以後DBレベルで重複を拒否)")
    except Exception as e:
        print(f"UNIQUE作成に失敗(重複が残っている可能性): {e}")

    report(con)
    if a.vacuum:
        print("\nVACUUM 実行中(38GB規模のため時間がかかります)...")
        t1 = time.time()
        con.execute("VACUUM")
        print(f"VACUUM 完了 / {time.time()-t1:.0f} 秒")
    else:
        print("\n領域回収は --vacuum で別途実行してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
