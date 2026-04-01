#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DB_PATH = WORKSPACE / "email_search.db"
STATUS_PATH = WORKSPACE / "email_search_integrity_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "dbPath": str(DB_PATH),
        "stage": "starting",
    }
    write_status(status)

    tmpdir = Path(tempfile.mkdtemp(prefix="email_db_integrity_"))
    copy_path = tmpdir / "email_search_copy.db"
    src_con = sqlite3.connect(DB_PATH)
    dst_con = sqlite3.connect(copy_path)
    try:
        src_con.backup(dst_con)
        dst_con.commit()
    finally:
        dst_con.close()
        src_con.close()

    con = sqlite3.connect(copy_path)
    try:
        integrity_rows = con.execute("PRAGMA integrity_check").fetchall()
        quick_rows = con.execute("PRAGMA quick_check").fetchall()
    finally:
        con.close()

    integrity = [row[0] for row in integrity_rows]
    quick = [row[0] for row in quick_rows]
    status["stage"] = "completed"
    status["finishedAt"] = now_jst_text()
    status["copyPath"] = str(copy_path)
    status["ok"] = integrity == ["ok"] and quick == ["ok"]
    status["integrityCheck"] = integrity
    status["quickCheck"] = quick
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
