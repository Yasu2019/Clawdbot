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
CHALLENGE = "Impulsive flux-inconsistent startup and incomplete pressure-energy-rheology closure"
STATUS = "root_cause_decided_staged_repair_full_geometry_hold"


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
        "Validate SI dimensions and pressure datum before launch. In the repaired full mesh, "
        "the first temperature excursion occurred at 1.200192e-7 s before Courant growth: "
        "internal U=0 conflicted with an instantaneous 0.05 m/s gate in a high-density-ratio "
        "compressible cavity, generating a pressure wave and later air velocity near 483.5 m/s. "
        "The screening T equation omits pressure-work/kinetic-energy coupling; Cross-WLF is "
        "not coupled to momentum and Tait is not in one conservative pressure closure. "
        "Repair sequentially: isothermal ramped hydraulic gate, conservative enthalpy gate, "
        "independent Cross-WLF/Tait validation and coupling, then two clean full repetitions. "
        "Never resume R1-R5 checkpoints."
    )


def register_local(text: str) -> str:
    with sqlite3.connect(LOCAL_DB) as conn:
        found = conn.execute(
            "SELECT 1 FROM growth_records WHERE domain=? AND artifact_path=? LIMIT 1",
            (DOMAIN, str(ARTIFACT)),
        ).fetchone()
        if found:
            conn.execute(
                """UPDATE growth_records SET challenge=?, status=?, know_how=?, evidence=?, source=?
                WHERE domain=? AND artifact_path=?""",
                (CHALLENGE, STATUS, text, "INC-OPENFOAM-035 T085 Beads vq3w.1-.3",
                 "register_openfoam_inc035_growth", DOMAIN, str(ARTIFACT)),
            )
            conn.commit()
            return "updated"
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
            await client.execute(
                """UPDATE growth_records SET challenge=?, status=?, know_how=?
                WHERE domain=? AND artifact_path=?""",
                [CHALLENGE, STATUS, text, DOMAIN, str(ARTIFACT)],
            )
            return "updated"
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
