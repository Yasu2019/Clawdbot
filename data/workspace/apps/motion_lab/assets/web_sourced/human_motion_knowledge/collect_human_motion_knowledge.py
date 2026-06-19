import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "downloads"
DB_PATH = ROOT / "human_motion_knowledge.db"
STATUS_PATH = ROOT / "human_motion_knowledge_status.json"
REPORT_PATH = ROOT / "human_motion_knowledge_report.md"


DIRECT_FREE_SOURCES = [
    {
        "id": "cmu_bvh_readme",
        "title": "CMU Motion Capture BVH Conversion README",
        "url": "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/READMEFIRST.txt",
        "publisher": "una-dinosauria GitHub mirror / CMU-derived BVH conversion",
        "category": "dataset_notes",
        "license_label": "direct_free",
        "format": "txt",
        "reason": "Contains practical retargeting notes: T-pose insertion, joint renaming, frame rate, shoulders, fingers, usage rights.",
    },
    {
        "id": "cmu_bvh_index",
        "title": "CMU Motion Capture BVH Conversion Index",
        "url": "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/cmu-mocap-index-text.txt",
        "publisher": "una-dinosauria GitHub mirror / CMU-derived BVH conversion",
        "category": "dataset_index",
        "license_label": "direct_free",
        "format": "txt",
        "reason": "Searchable index for walking and locomotion clips before downloading individual motion files.",
    },
    {
        "id": "mwni_blender_retargeting_readme",
        "title": "Blender Animation Retargeting Add-on README",
        "url": "https://raw.githubusercontent.com/Mwni/blender-animation-retargeting/master/README.md",
        "publisher": "Mwni GitHub",
        "category": "tooling",
        "license_label": "direct_free",
        "format": "md",
        "reason": "Practical Blender retargeting workflow and foot/hand correction guidance.",
    },
    {
        "id": "contact_aware_retargeting_iccv2021",
        "title": "Contact-Aware Retargeting of Skinned Motion",
        "url": "https://openaccess.thecvf.com/content/ICCV2021/papers/Villegas_Contact-Aware_Retargeting_of_Skinned_Motion_ICCV_2021_paper.pdf",
        "publisher": "CVF Open Access",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Explains preserving ground/self-contact to avoid foot sliding and interpenetration.",
    },
    {
        "id": "non_humanoid_human_motion_disney2010",
        "title": "Animating Non-Humanoid Characters with Human Motion Data",
        "url": "https://la.disneyresearch.com/wp-content/uploads/Animating-Non-Humanoid-Characters-with-Human-Motion-Data-Paper.pdf",
        "publisher": "Disney Research / Eurographics SCA",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Useful for mecha or proportion-mismatched models: map key poses then optimize physical realism.",
    },
    {
        "id": "correspondence_free_online_retargeting_3dv",
        "title": "Correspondence-free Online Human Motion Retargeting",
        "url": "https://inria.hal.science/hal-03970689/file/motion_retargeting_3DV_preprint_.pdf",
        "publisher": "HAL-Inria",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Modern unsupervised retargeting reference for source-target skeleton mismatch.",
    },
    {
        "id": "dense_geometric_interaction_retargeting_neurips2024",
        "title": "Skinned Motion Retargeting with Dense Geometric Interaction Perception",
        "url": "https://papers.nips.cc/paper_files/paper/2024/file/e3ed7183233afa8e5485ff8f6c3f18b1-Paper-Conference.pdf",
        "publisher": "NeurIPS proceedings",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Recent geometry-aware retargeting reference for stylized/cartoon targets.",
    },
    {
        "id": "general_motion_retargeting_humanoid_icra",
        "title": "General Motion Retargeting for Humanoid Motion Tracking",
        "url": "https://jiajunwu.com/papers/gmr_icra.pdf",
        "publisher": "Author-hosted paper",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Kinematic retargeting reference with embodiment gap framing.",
    },
    {
        "id": "rokoko_blender_retargeting",
        "title": "Retarget an animation in Blender",
        "url": "https://support.rokoko.com/hc/en-us/articles/4410463481489-Retarget-an-animation-in-Blender",
        "publisher": "Rokoko Support",
        "category": "tooling",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Blender plugin retargeting steps and import/bone-list workflow.",
    },
    {
        "id": "sidefx_cmu_kinefx_retargeting",
        "title": "Retarget the CMU Motion Capture Database",
        "url": "https://www.sidefx.com/tutorials/retarget-the-cmu-motion-capture-database-19_5/",
        "publisher": "SideFX",
        "category": "tooling",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Procedural cleanup/noise removal and KineFX retargeting workflow for CMU data.",
    },
]


ACQUISITION_QUEUE = [
    {
        "id": "amass_dataset",
        "title": "AMASS human motion archive",
        "url": "https://amass.is.tue.mpg.de/",
        "status": "free_registration",
        "next_action": "Review license and register/authorize before download.",
    },
    {
        "id": "smpl_model",
        "title": "SMPL body model",
        "url": "https://smpl.is.tue.mpg.de/",
        "status": "free_registration",
        "next_action": "Review license; needed only if SMPL-based retargeting pipeline is adopted.",
    },
    {
        "id": "mixamo",
        "title": "Adobe Mixamo motions",
        "url": "https://www.mixamo.com/",
        "status": "free_registration",
        "next_action": "Use only through authorized account and current Adobe terms; avoid bulk scraping.",
    },
    {
        "id": "mocap_online_free_pack",
        "title": "MoCap Online Free Pack",
        "url": "https://mocaponline.com/",
        "status": "manual_review",
        "next_action": "Review current checkout/license terms before asset download.",
    },
    {
        "id": "makehuman_makewalk_wiki",
        "title": "MakeWalk Blender BVH Retargeting Documentation",
        "url": "https://www.makehumancommunity.org/wiki/Documentation%3AMakeWalk",
        "status": "manual_review",
        "next_action": "Useful source, but direct download from this host returned connection refused in the bounded run; retry later or capture metadata only.",
    },
]


LESSONS = [
    ("retargeting_preflight", "Match or explicitly map skeleton hierarchy from root outward; mismatched shoulder/hip/clavicle assumptions are a common cause of unnatural arms and torso."),
    ("t_pose_baseline", "Store a clean reference pose before applying motion. CMU BVH conversions add a first-frame T-pose because retargeting quality depends on rest-pose alignment."),
    ("root_motion_policy", "Decide early whether root translation is preserved, baked to hips, or constrained. Natural walking needs coherent root travel; copying all object transforms blindly can launch scaled models out of frame."),
    ("foot_contact", "Detect stance phases and lock/support feet during ground contact to reduce sliding. Add IK foot correction when source and target proportions differ."),
    ("contact_geometry", "Skeleton-only retargeting misses self-contact and mesh interpenetration. For production, run geometry/contact checks for hands, feet, torso, and armor plates."),
    ("mecha_or_nonhuman", "For mecha/proportion-mismatched characters, use human motion as intent, not literal joint data. Build key-pose correspondences and optimize readable, physically plausible target poses."),
    ("frame_rate", "Preserve source frame rate metadata. CMU data was captured at 120 fps; wrong frame timing changes perceived gait weight and speed."),
    ("ignore_uncaptured_digits", "Ignore finger/thumb joints when the source dataset says they were not captured. Dead channels can create noisy or misleading target poses."),
]


def fetch(url: str, timeout: int = 45) -> bytes:
    req = Request(url, headers={"User-Agent": "Clawstack-MotionKnowledgeScout/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def safe_name(source: dict) -> str:
    suffix = source["format"].lower()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source["id"]).strip("_")
    return f"{stem}.{suffix}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            publisher TEXT,
            category TEXT,
            access_date TEXT NOT NULL,
            license_label TEXT NOT NULL,
            status TEXT NOT NULL,
            local_path TEXT,
            sha256 TEXT,
            bytes INTEGER,
            reason TEXT,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY,
            lesson TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS acquisition_queue (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            next_action TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            query_scope TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            downloaded_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS motion_candidates (
            clip_id TEXT PRIMARY KEY,
            subject TEXT,
            description TEXT NOT NULL,
            source_id TEXT NOT NULL,
            candidate_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def upsert_source(conn: sqlite3.Connection, source: dict, status: str, local_path: str = "", digest: str = "", size: int = 0, error: str = "") -> None:
    conn.execute(
        """
        INSERT INTO sources
        (id, title, url, publisher, category, access_date, license_label, status, local_path, sha256, bytes, reason, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            url=excluded.url,
            publisher=excluded.publisher,
            category=excluded.category,
            access_date=excluded.access_date,
            license_label=excluded.license_label,
            status=excluded.status,
            local_path=excluded.local_path,
            sha256=excluded.sha256,
            bytes=excluded.bytes,
            reason=excluded.reason,
            error=excluded.error
        """,
        (
            source["id"],
            source["title"],
            source["url"],
            source.get("publisher", ""),
            source.get("category", ""),
            datetime.now(timezone.utc).isoformat(),
            source["license_label"],
            status,
            local_path,
            digest,
            size,
            source.get("reason", ""),
            error,
        ),
    )


def write_report(downloaded: list[dict], failed: list[dict]) -> None:
    now = datetime.now().astimezone().isoformat()
    lines = [
        "# Human Motion Retargeting Knowledge Scout",
        "",
        f"- generated_at: {now}",
        "- adoption: ADOPT_PARTIAL into existing motion_lab web_sourced knowledge store",
        "- legal_policy: metadata-first; direct_free downloads only; registration/paid/unclear sources queued",
        "- scope: human walking, mocap retargeting, root motion, foot contact, skeleton/proportion mismatch",
        "",
        "## Downloaded Direct-Free Sources",
        "",
        "| id | category | bytes | local_path |",
        "| --- | --- | ---: | --- |",
    ]
    for item in downloaded:
        lines.append(f"| {item['id']} | {item['category']} | {item['bytes']} | `{item['local_path']}` |")
    lines.extend(["", "## Failed Direct-Free Attempts", ""])
    if failed:
        lines.extend(["| id | url | error |", "| --- | --- | --- |"])
        for item in failed:
            lines.append(f"| {item['id']} | {item['url']} | {item['error'].replace('|', '/')} |")
    else:
        lines.append("- none")
    candidate_count = 0
    candidate_path = ROOT / "cmu_locomotion_candidates.json"
    if candidate_path.exists():
        try:
            candidate_count = len(json.loads(candidate_path.read_text(encoding="utf-8")))
        except Exception:
            candidate_count = 0
    lines.extend([
        "",
        "## Practical Rules Extracted",
        "",
    ])
    for key, lesson in LESSONS:
        lines.append(f"- **{key}**: {lesson}")
    lines.extend([
        "",
        "## Acquisition Queue",
        "",
        "| id | status | next_action |",
        "| --- | --- | --- |",
    ])
    for item in ACQUISITION_QUEUE:
        lines.append(f"| {item['id']} | {item['status']} | {item['next_action']} |")
    lines.extend([
        "",
        "## Indexed Motion Candidates",
        "",
        f"- CMU locomotion candidate rows: {candidate_count}",
        f"- JSON export: `{candidate_path.name}`",
        "",
        "## Next Implementation Use",
        "",
        "- Add a motion QA gate: foot-contact slide distance, root-travel consistency, knee/hip range, and mesh interpenetration.",
        "- For existing Mixamo/CMU motions, prefer rotation-only bone curves plus explicit root-motion policy.",
        "- For mecha models, use key-pose intent mapping and IK/contact correction instead of literal human joint transfer.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_cmu_locomotion_candidates(conn: sqlite3.Connection, now: str) -> int:
    index_path = DOWNLOADS / "cmu_bvh_index.txt"
    if not index_path.exists():
        return 0
    text = index_path.read_text(encoding="utf-8", errors="replace")
    subject = ""
    rows = []
    pattern = re.compile(r"^(\d{2}_\d{2})\s+(.+)$")
    locomotion = re.compile(r"\b(walk|walking|run|jog|gait|stride|limp|march|stroll)\b", re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Subject #"):
            subject = line
            continue
        match = pattern.match(line)
        if not match:
            continue
        clip_id, description = match.groups()
        if not locomotion.search(description):
            continue
        candidate_type = "walk" if re.search(r"\bwalk|walking|stroll|stride|gait|limp\b", description, re.IGNORECASE) else "run"
        rows.append(
            {
                "clip_id": clip_id,
                "subject": subject,
                "description": description,
                "source_id": "cmu_bvh_index",
                "candidate_type": candidate_type,
            }
        )
    conn.execute("DELETE FROM motion_candidates WHERE source_id = ?", ("cmu_bvh_index",))
    conn.executemany(
        """
        INSERT INTO motion_candidates(clip_id, subject, description, source_id, candidate_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(row["clip_id"], row["subject"], row["description"], row["source_id"], row["candidate_type"], now) for row in rows],
    )
    (ROOT / "cmu_locomotion_candidates.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(rows)


def main() -> int:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    current_source_ids = [source["id"] for source in DIRECT_FREE_SOURCES]
    placeholders = ",".join("?" for _ in current_source_ids)
    conn.execute(f"DELETE FROM sources WHERE id NOT IN ({placeholders})", current_source_ids)
    downloaded = []
    failed = []
    for source in DIRECT_FREE_SOURCES:
        filename = safe_name(source)
        target = DOWNLOADS / filename
        try:
            data = fetch(source["url"])
            target.write_bytes(data)
            digest = sha256_bytes(data)
            item = {
                "id": source["id"],
                "category": source["category"],
                "bytes": len(data),
                "local_path": str(target.relative_to(ROOT)),
                "sha256": digest,
            }
            downloaded.append(item)
            upsert_source(conn, source, "downloaded", item["local_path"], digest, len(data))
            print(f"[OK] {source['id']} {len(data)} bytes")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            failed.append({"id": source["id"], "url": source["url"], "error": error})
            upsert_source(conn, source, "failed", error=error)
            print(f"[NG] {source['id']} {error}")
    now = datetime.now(timezone.utc).isoformat()
    candidate_count = extract_cmu_locomotion_candidates(conn, now)
    for key, lesson in LESSONS:
        conn.execute(
            "INSERT INTO lessons(id, lesson, created_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET lesson=excluded.lesson",
            (key, lesson, now),
        )
    for item in ACQUISITION_QUEUE:
        conn.execute(
            """
            INSERT INTO acquisition_queue(id, title, url, status, next_action, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                url=excluded.url,
                status=excluded.status,
                next_action=excluded.next_action
            """,
            (item["id"], item["title"], item["url"], item["status"], item["next_action"], now),
        )
    conn.execute(
        "INSERT INTO run_log(run_at, query_scope, source_count, downloaded_count, failed_count) VALUES (?, ?, ?, ?, ?)",
        (now, "human motion retargeting walking natural 3D model", len(DIRECT_FREE_SOURCES), len(downloaded), len(failed)),
    )
    conn.commit()
    conn.close()
    status = {
        "generated_at": now,
        "db_path": str(DB_PATH),
        "report_path": str(REPORT_PATH),
        "download_dir": str(DOWNLOADS),
        "source_count": len(DIRECT_FREE_SOURCES),
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "downloaded": downloaded,
        "failed": failed,
        "acquisition_queue": ACQUISITION_QUEUE,
        "cmu_locomotion_candidate_count": candidate_count,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(downloaded, failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
