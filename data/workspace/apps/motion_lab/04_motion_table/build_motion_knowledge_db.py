import csv
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
MOTION_TABLE = ROOT / "data/workspace/apps/motion_lab/04_motion_table"
REGISTRY_CSV = MOTION_TABLE / "motion_asset_learning_registry.csv"
DB_PATH = MOTION_TABLE / "motion_knowledge.db"
INSPECTION_GLOB = "mixamo_*_asset_inspection_20260503.json"


LESSONS = [
    (
        "mixamo_standard_skeleton",
        "Mixamo FBX files inspected on 2026-05-03 use mixamorig:* bones with finger bones.",
        "Treat Mixamo files as the first retarget target. Build correction layers around shoulder, forearm, wrist, and hand continuity.",
    ),
    (
        "iatf_first_cut_recipe",
        "A practical first IATF cut is Walking/Walker Walk -> Idle -> Talking (3) -> Pointing (2).",
        "Use this sequence for the next seven-frame diagnostic render before MP4.",
    ),
    (
        "long_meeting_clips",
        "Meeting clips are 1401-frame long-form actions.",
        "Do not use entire meeting clips. Extract 3-5 second listening, nodding, or subtle reaction spans.",
    ),
    (
        "phone_and_fight_low_priority",
        "Phone, fight, ninja, kneeling, and laying clips are structurally valid but usually unsuitable for formal IATF instruction.",
        "Keep them in the registry with low priority; only use when a script explicitly needs that posture.",
    ),
    (
        "diagnostic_gate",
        "MP4 should be created only after seven diagnostic frames pass identity, motion variation, mouth, blink, arm continuity, and slide-content checks.",
        "Keep sample_frames_are_nearly_identical as a hard stop.",
    ),
]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS motion_assets (
            asset_id TEXT PRIMARY KEY,
            source TEXT,
            source_url TEXT,
            license_status TEXT,
            cost_jpy_estimate TEXT,
            format TEXT,
            skeleton_hint TEXT,
            tags TEXT,
            intended_iatf_use TEXT,
            local_path TEXT,
            status TEXT,
            quality_score TEXT,
            known_issues TEXT,
            next_action TEXT,
            last_reviewed TEXT
        );

        CREATE TABLE IF NOT EXISTS motion_inspections (
            name TEXT PRIMARY KEY,
            path TEXT,
            ok INTEGER,
            frame_min REAL,
            frame_max REAL,
            armatures TEXT,
            actions_json TEXT,
            bone_samples_json TEXT,
            inspected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS motion_lessons (
            lesson_id TEXT PRIMARY KEY,
            observation TEXT NOT NULL,
            rule TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def import_registry(conn: sqlite3.Connection) -> int:
    count = 0
    with REGISTRY_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            conn.execute(
                """
                INSERT OR REPLACE INTO motion_assets (
                    asset_id, source, source_url, license_status, cost_jpy_estimate,
                    format, skeleton_hint, tags, intended_iatf_use, local_path, status,
                    quality_score, known_issues, next_action, last_reviewed
                ) VALUES (
                    :asset_id, :source, :source_url, :license_status, :cost_jpy_estimate,
                    :format, :skeleton_hint, :tags, :intended_iatf_use, :local_path, :status,
                    :quality_score, :known_issues, :next_action, :last_reviewed
                )
                """,
                row,
            )
            count += 1
    return count


def import_inspections(conn: sqlite3.Connection) -> int:
    count = 0
    for path in sorted(MOTION_TABLE.glob(INSPECTION_GLOB)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("results", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO motion_inspections (
                    name, path, ok, frame_min, frame_max, armatures,
                    actions_json, bone_samples_json, inspected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("name"),
                    item.get("path"),
                    1 if item.get("ok") else 0,
                    item.get("frame_min"),
                    item.get("frame_max"),
                    "|".join(item.get("armatures") or []),
                    json.dumps(item.get("actions") or [], ensure_ascii=False),
                    json.dumps(item.get("bone_samples") or [], ensure_ascii=False),
                    "2026-05-03",
                ),
            )
            count += 1
    return count


def import_lessons(conn: sqlite3.Connection) -> int:
    for lesson_id, observation, rule in LESSONS:
        conn.execute(
            """
            INSERT OR REPLACE INTO motion_lessons (
                lesson_id, observation, rule, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (lesson_id, observation, rule, "2026-05-03"),
        )
    return len(LESSONS)


def main() -> int:
    conn = connect()
    try:
        create_schema(conn)
        assets = import_registry(conn)
        inspections = import_inspections(conn)
        lessons = import_lessons(conn)
        conn.commit()
        print(json.dumps({
            "db": str(DB_PATH),
            "assets": assets,
            "inspections": inspections,
            "lessons": lessons,
        }, ensure_ascii=False, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
