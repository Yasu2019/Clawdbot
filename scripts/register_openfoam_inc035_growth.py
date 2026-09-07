"""Register INC-OPENFOAM-035 knowledge in local growth DB and Turso."""
from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs" / "incidents" / "20260908_box_roundhole_polymerinterfoam_resume_hold.md"
LOCAL_DB = ROOT / "data" / "workspace" / "universal_growth.db"
DOMAIN = "OpenFOAM polymerInterFoam restart safety"
CHALLENGE = "Invalid unit scale and pressure datum made all restart checkpoints nonphysical"
STATUS = "hold_after_three_recovery_trials_inc_openfoam_035"


def load_turso_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in {"TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"}:
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def knowledge() -> str:
    return (
        "Validate mesh dimensions against the canonical SI specification before launch. "
        "The failed 100x60x50 mm part was meshed as 100x60x50 m and p_rgh mixed a "
        "101325 Pa internal datum with a 0 Pa vent. Reject restart checkpoints by field "
        "and Courant gates, not merely by time-directory presence. R2 exceeded the "
        "temperature gate; R3/R4 collapsed in timestep near 2.58e-4 s. Full continuation "
        "is HOLD after three trials; run the minimal SI conservation benchmark first."
    )


def register_local(text: str) -> str:
    with sqlite3.connect(LOCAL_DB) as conn:
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
            (DOMAIN, CHALLENGE, STATUS, text, str(ARTIFACT), 5,
             "INC-OPENFOAM-035 T085 Beads vq3w/o9io", "register_openfoam_inc035_growth"),
        )
        conn.commit()
    return "inserted"


async def register_turso(text: str) -> str:
    load_turso_env()
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
            [DOMAIN, CHALLENGE, STATUS, text, str(ARTIFACT)],
        )
        return "inserted"
    finally:
        await client.close()


async def main() -> None:
    text = knowledge()
    print(f"local={register_local(text)}")
    print(f"turso={await register_turso(text)}")


if __name__ == "__main__":
    asyncio.run(main())
