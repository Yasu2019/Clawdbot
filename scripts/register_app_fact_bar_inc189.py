# -*- coding: utf-8 -*-
"""Register INC-189 / T082 app FACT-bar know-how to local growth DB and Turso."""
from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs" / "knowledge" / "app_page_fact_bar_cetol_viai_20260827.md"
LOCAL_DB = ROOT / "data" / "workspace" / "universal_growth.db"
DOMAIN = "Portal app FACT bar CETOL VIAI CAE"
CHALLENGE = "Silent inline JS parse failure hid STALE CETOL reports; pages lacked dated FACT"
STATUS = "recorded_inc189_t082_2026-08-28"


def load_selected_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in {"TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"}:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def register_local(know_how: str) -> str:
    LOCAL_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(LOCAL_DB) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            domain TEXT, challenge TEXT, status TEXT, know_how TEXT, artifact_path TEXT,
            difficulty INTEGER, evidence TEXT, source TEXT)"""
        )
        found = conn.execute(
            "SELECT 1 FROM growth_records WHERE domain=? AND artifact_path=? LIMIT 1",
            (DOMAIN, str(ARTIFACT)),
        ).fetchone()
        if found:
            return "already_present"
        conn.execute(
            """INSERT INTO growth_records
            (domain, challenge, status, know_how, artifact_path, difficulty, evidence, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                DOMAIN,
                CHALLENGE,
                STATUS,
                know_how,
                str(ARTIFACT),
                3,
                "INC-189 T082 S033 browser FACT bars 2026-08-27",
                "record_app_fact_bar_inc189",
            ),
        )
        conn.commit()
    return "inserted"


async def register_turso(know_how: str) -> str:
    load_selected_env()
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if not url or not token:
        return "skipped_missing_credentials"
    try:
        import libsql_client
    except ImportError:
        return "skipped_missing_libsql_client"
    client = libsql_client.create_client(url=url, auth_token=token)
    try:
        result = await client.execute(
            "SELECT id FROM growth_records WHERE domain=? AND artifact_path=? LIMIT 1",
            [DOMAIN, str(ARTIFACT)],
        )
        if result.rows:
            return "already_present"
        await client.execute(
            """INSERT INTO growth_records
            (domain, challenge, status, know_how, artifact_path)
            VALUES (?, ?, ?, ?, ?)""",
            [DOMAIN, CHALLENGE, STATUS, know_how[:8000], str(ARTIFACT)],
        )
        return "inserted"
    finally:
        await client.close()


def main() -> None:
    know_how = ARTIFACT.read_text(encoding="utf-8")
    if "\ufffd" in know_how or any(m in know_how for m in "縺繧繝"):
        raise SystemExit("artifact encoding check failed")
    print(f"local={register_local(know_how)}")
    print(f"turso={asyncio.run(register_turso(know_how))}")


if __name__ == "__main__":
    main()
