import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "downloads"
DB_PATH = ROOT / "robotics_gait_knowledge.db"
STATUS_PATH = ROOT / "robotics_gait_knowledge_status.json"
REPORT_PATH = ROOT / "robotics_gait_knowledge_report.md"


DIRECT_FREE_SOURCES = [
    {
        "id": "mit_underactuated_humanoids",
        "title": "Underactuated Robotics: Highly-Articulated Legged Robots",
        "url": "https://underactuated.mit.edu/humanoids.html",
        "publisher": "MIT Underactuated Robotics",
        "category": "course_notes",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Explains center-of-mass, angular momentum, foot placement, and humanoid walking abstractions.",
    },
    {
        "id": "kajita_preview_control_zmp",
        "title": "Biped Walking Pattern Generation by using Preview Control of Zero-Moment Point",
        "url": "https://mzucker.github.io/swarthmore/e91_s2013/readings/kajita2003preview.pdf",
        "publisher": "Kajita et al. mirror used in robotics course material",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Canonical ZMP preview control reference for smooth CoM/root motion planning.",
    },
    {
        "id": "dekker_zmp_stable_biped",
        "title": "Zero-Moment Point Method for Stable Biped Walking",
        "url": "https://techunited.nl/media/files/humanoid/MaartenDekker_OPEN2009_Zero_Moment_Point_Method_for_Stable_Biped_Walking.pdf",
        "publisher": "Tech United / Eindhoven",
        "category": "thesis_report",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Practical ZMP, walking primitives, and inverse differential kinematics guidance.",
    },
    {
        "id": "sardain_bessonnet_cop_zmp",
        "title": "Forces Acting on a Biped Robot. Center of Pressure - Zero Moment Point",
        "url": "https://www.cs.cmu.edu/~cga/legs/sardain-bessonnet.pdf",
        "publisher": "CMU-hosted paper",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Clarifies CoP/ZMP definitions and support-area stability checks.",
    },
    {
        "id": "auxiliary_zmp_walking_generator",
        "title": "Biped Walking Pattern Generator allowing Auxiliary ZMP Control",
        "url": "https://www.cs.cmu.edu/~jkh/gnhm_08/2008_04_14.Biped%20Walking%20Pattern%20Generator%20allowing%20Auxiliary%20ZMP%20Control.pdf",
        "publisher": "CMU-hosted workshop material",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Useful for uneven-ground and stabilizing reference trajectory ideas.",
    },
    {
        "id": "durus_dynamic_efficient_bipedal_locomotion",
        "title": "Realizing Dynamic and Efficient Bipedal Locomotion on the Humanoid Robot DURUS",
        "url": "https://mae.osu.edu/sites/default/files/2021-06/reher2016realizing.pdf",
        "publisher": "Ohio State MAE / DURUS authors",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Connects hardware-aware biped locomotion, gait events, foot placement, and efficient walking behavior.",
    },
    {
        "id": "rss_multicontact_feasibility",
        "title": "Learning Feasibility Constraints for Multi-contact Locomotion of Legged Robots",
        "url": "https://www.roboticsproceedings.org/rss13/p31.pdf",
        "publisher": "Robotics: Science and Systems",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Gives feasibility framing for whole-body IK and centroidal/contact constraints.",
    },
    {
        "id": "pmc_heel_contact_toe_off",
        "title": "Kid-size robot humanoid walking with heel-contact and toe-off motion",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9044359/",
        "publisher": "PMC / Sensors",
        "category": "paper_html",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Human-like walking details: heel contact, toe-off, DCM/CoM planning, and phase timing.",
    },
    {
        "id": "pmc_omnidirectional_walking_generator",
        "title": "Omnidirectional Walking Pattern Generator Combining Virtual Constraints and Preview Control",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8284058/",
        "publisher": "PMC / Sensors",
        "category": "paper_html",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Reference for turning and omnidirectional walk patterns instead of straight-line-only gait.",
    },
    {
        "id": "mit_littledog_dynamic_ik",
        "title": "Inverse Kinematics for a Point-Foot Quadruped Robot with Dynamic Redundancy Resolution",
        "url": "https://groups.csail.mit.edu/robotics-center/public_papers/Shkolnik07.pdf",
        "publisher": "MIT CSAIL",
        "category": "paper",
        "license_label": "direct_free",
        "format": "pdf",
        "reason": "Not humanoid, but useful for CoM/swing-leg IK and dynamic redundancy ideas.",
    },
    {
        "id": "isaac_lab_robot_learning_docs",
        "title": "Isaac Lab: Unified Framework for Robot Learning",
        "url": "https://isaac-sim.github.io/IsaacLab/",
        "publisher": "NVIDIA / Isaac Lab Project",
        "category": "robot_learning_framework",
        "license_label": "direct_free",
        "format": "html",
        "reason": "GPU-accelerated robot learning framework for scalable RL/IL, vectorized environments, and sim-to-real workflows.",
    },
    {
        "id": "isaac_lab_imitation_learning_docs",
        "title": "Isaac Lab Imitation Learning",
        "url": "https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/index.html",
        "publisher": "NVIDIA / Isaac Lab Project",
        "category": "imitation_learning",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Reference for using demonstrations and imitation learning instead of hand-programming every motion.",
    },
    {
        "id": "behavior_1k_project",
        "title": "BEHAVIOR-1K Project Website",
        "url": "https://behavior.stanford.edu/index.html",
        "publisher": "Stanford Vision and Learning Lab",
        "category": "household_embodied_ai",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Defines human-centered household tasks and long-horizon activities for domestic robot training.",
    },
    {
        "id": "behavior_1k_pmlr",
        "title": "BEHAVIOR-1K: A Benchmark for Embodied AI with 1,000 Everyday Activities and Realistic Simulation",
        "url": "https://proceedings.mlr.press/v205/li23a.html",
        "publisher": "PMLR / CoRL",
        "category": "household_embodied_ai_paper",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Paper metadata and abstract for long-horizon household activities, OmniGibson simulation, and sim-to-real framing.",
    },
    {
        "id": "robocasa_project",
        "title": "RoboCasa",
        "url": "https://robocasa.ai/",
        "publisher": "RoboCasa Project",
        "category": "kitchen_robot_learning",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Large-scale kitchen task simulation and benchmark direction for household robot manipulation.",
    },
    {
        "id": "robocasa_github",
        "title": "RoboCasa GitHub Repository",
        "url": "https://github.com/robocasa/robocasa",
        "publisher": "RoboCasa Project / GitHub",
        "category": "kitchen_robot_learning_source",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Implementation entry point for kitchen robot learning simulation; code/license must be reviewed before reuse.",
    },
    {
        "id": "ros_industrial_home",
        "title": "ROS-Industrial",
        "url": "https://rosindustrial.org/",
        "publisher": "ROS-Industrial Consortium",
        "category": "factory_robotics",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Industrial robot integration patterns, hardware drivers, training curriculum, and factory application references.",
    },
    {
        "id": "ros_industrial_training_docs",
        "title": "ROS-Industrial Training Documentation",
        "url": "https://industrial-training-master.readthedocs.io/",
        "publisher": "ROS-Industrial",
        "category": "factory_robotics_training",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Practical training structure for ROS and industrial robot applications.",
    },
    {
        "id": "unity_ml_agents_docs",
        "title": "Unity ML-Agents Toolkit",
        "url": "https://unity-technologies.github.io/ml-agents/",
        "publisher": "Unity Technologies",
        "category": "multi_agent_visual_training",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Multi-agent reinforcement/imitation learning and user-visible simulation scenes.",
    },
    {
        "id": "unreal_learning_agents_docs",
        "title": "Unreal Engine Learning Agents",
        "url": "https://dev.epicgames.com/documentation/en-us/unreal-engine/learning-agents-in-unreal-engine",
        "publisher": "Epic Games",
        "category": "high_fidelity_agent_training",
        "license_label": "direct_free",
        "format": "html",
        "reason": "High-fidelity visual agent training and interactive demos for later-stage user presentation.",
    },
    {
        "id": "micro_ros_overview",
        "title": "micro-ROS",
        "url": "https://micro.ros.org/",
        "publisher": "Open Robotics / micro-ROS Project",
        "category": "edge_robot_control",
        "license_label": "direct_free",
        "format": "html",
        "reason": "Bridge from ROS 2-style high-level behavior to microcontroller-level robot actuation.",
    },
]


ACQUISITION_QUEUE = [
    {
        "id": "ieee_recent_humanoid_foot_placement",
        "title": "Recent IEEE humanoid foot placement papers",
        "url": "https://ieeexplore.ieee.org/",
        "status": "paid_or_subscription",
        "next_action": "Use metadata only unless institutional access/licensing is confirmed.",
    },
    {
        "id": "springer_zmp_chapters",
        "title": "Springer ZMP and humanoid walking chapters",
        "url": "https://link.springer.com/",
        "status": "paid_or_subscription",
        "next_action": "Queue for manual review; do not download chapters behind access control.",
    },
    {
        "id": "robotis_op3_walking_source",
        "title": "ROBOTIS OP3 walking module source and docs",
        "url": "https://github.com/ROBOTIS-GIT/ROBOTIS-OP3",
        "status": "manual_review",
        "next_action": "Review license and extract implementation notes separately if useful.",
    },
    {
        "id": "drake_humanoid_examples",
        "title": "Drake humanoid/legged examples",
        "url": "https://drake.mit.edu/",
        "status": "manual_review",
        "next_action": "Review current examples and license before importing code or formulas.",
    },
    {
        "id": "behavior_1k_dataset_assets",
        "title": "BEHAVIOR-1K / OmniGibson assets",
        "url": "https://github.com/StanfordVL/BEHAVIOR-1K",
        "status": "manual_review",
        "next_action": "Review license, disk size, simulator requirements, and access rules before downloading assets.",
    },
    {
        "id": "robocasa_kitchen_assets",
        "title": "RoboCasa kitchen assets and demonstration data",
        "url": "https://github.com/robocasa/robocasa",
        "status": "manual_review",
        "next_action": "Review license/terms and size before downloading kitchen assets or demonstrations.",
    },
    {
        "id": "isaac_sim_installation",
        "title": "Isaac Sim / Isaac Lab installation assets",
        "url": "https://developer.nvidia.com/isaac/sim",
        "status": "manual_review",
        "next_action": "Install only after GPU/driver compatibility check and user approval for large downloads.",
    },
    {
        "id": "raspberry_pi_ai_kit",
        "title": "Raspberry Pi AI Kit",
        "url": "https://www.raspberrypi.com/products/ai-kit/",
        "status": "manual_review",
        "next_action": "Official site returned HTTP 403 to automated fetch; keep metadata only and review manually in browser.",
    },
]


ALGORITHM_RULES = [
    {
        "id": "support_polygon_gate",
        "priority": 1,
        "metric": "projected_com_inside_support_polygon",
        "rule": "During stance or double support, projected CoM should remain within the support polygon plus a small visual tolerance.",
        "motion_use": "Reject or correct frames where the character appears to tip despite planted feet.",
        "source_ids": ["mit_underactuated_humanoids", "sardain_bessonnet_cop_zmp", "dekker_zmp_stable_biped"],
    },
    {
        "id": "foot_contact_lock",
        "priority": 1,
        "metric": "stance_foot_world_velocity",
        "rule": "When a foot is in stance phase, world-space foot translation should be near zero unless intentional slip is authored.",
        "motion_use": "Lock planted foot, solve pelvis/knee with IK, and release at toe-off.",
        "source_ids": ["pmc_heel_contact_toe_off", "durus_dynamic_efficient_bipedal_locomotion"],
    },
    {
        "id": "heel_toe_phase",
        "priority": 2,
        "metric": "heel_strike_toe_off_timing",
        "rule": "A walking step reads more naturally when heel contact, flat support, and toe-off phases are distinguishable.",
        "motion_use": "Add keyframe markers or foot roll constraints around contact transitions.",
        "source_ids": ["pmc_heel_contact_toe_off"],
    },
    {
        "id": "root_com_smoothing",
        "priority": 2,
        "metric": "root_speed_variation",
        "rule": "Root/CoM path should be smooth and coherent with step cadence; abrupt root speed changes break walking weight.",
        "motion_use": "Low-pass smooth pelvis/root travel and keep stride distance consistent with footfall timing.",
        "source_ids": ["kajita_preview_control_zmp", "pmc_omnidirectional_walking_generator"],
    },
    {
        "id": "swing_foot_clearance",
        "priority": 2,
        "metric": "swing_foot_clearance",
        "rule": "Swing foot should clear the ground enough to avoid visual scraping but not float excessively.",
        "motion_use": "Clamp swing arc to model scale and terrain height.",
        "source_ids": ["auxiliary_zmp_walking_generator", "mit_littledog_dynamic_ik"],
    },
    {
        "id": "ik_continuity_gate",
        "priority": 1,
        "metric": "joint_angle_delta",
        "rule": "IK corrections must preserve temporal continuity; knee/ankle/hip jumps are worse than mild pose error.",
        "motion_use": "Use bounded per-frame joint deltas and smooth correction weights across contact phases.",
        "source_ids": ["rss_multicontact_feasibility", "mit_littledog_dynamic_ik"],
    },
    {
        "id": "vectorized_experience_collection",
        "priority": 1,
        "metric": "parallel_rollout_count",
        "rule": "Many robots/environments should collect short rollouts in parallel, while only selected episodes are rendered for human review.",
        "motion_use": "Train headless at scale, then export score, success/NG, collision, energy, and GIF/GLB evidence for dashboard inspection.",
        "source_ids": ["isaac_lab_robot_learning_docs", "unity_ml_agents_docs"],
    },
    {
        "id": "household_task_curriculum",
        "priority": 1,
        "metric": "task_success_by_curriculum_stage",
        "rule": "Household autonomy should progress from approach and posture tasks to long-horizon object-state tasks.",
        "motion_use": "Score simple robot tasks as walk -> reach -> open/close -> sit/stand -> multi-step kitchen or care assistance.",
        "source_ids": ["behavior_1k_project", "behavior_1k_pmlr", "robocasa_project"],
    },
    {
        "id": "factory_task_curriculum",
        "priority": 1,
        "metric": "cycle_success_safety_and_alignment",
        "rule": "Factory robot policies must track task success together with safety-zone, collision, force, alignment, and cycle-time constraints.",
        "motion_use": "Add separate factory reward terms for fixture alignment, part handling, safety-zone avoidance, and failed-grasp recovery.",
        "source_ids": ["ros_industrial_home", "ros_industrial_training_docs"],
    },
    {
        "id": "sim_to_edge_deployment_gate",
        "priority": 1,
        "metric": "edge_policy_safety_readiness",
        "rule": "Real robot deployment requires a restricted edge controller, emergency stop, speed/force limits, and simulator-to-hardware validation.",
        "motion_use": "Convert learned behaviors into Raspberry Pi/ROS 2/microcontroller profiles only after offline replay and safety gates pass.",
        "source_ids": ["micro_ros_overview", "raspberry_pi_ai_kit"],
    },
]


def fetch(url: str, timeout: int = 45) -> bytes:
    req = Request(url, headers={"User-Agent": "Clawstack-RoboticsGaitScout/1.0"})
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
        CREATE TABLE IF NOT EXISTS algorithm_rules (
            id TEXT PRIMARY KEY,
            priority INTEGER NOT NULL,
            metric TEXT NOT NULL,
            rule TEXT NOT NULL,
            motion_use TEXT NOT NULL,
            source_ids TEXT NOT NULL,
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
        "# Robotics Gait Knowledge Scout",
        "",
        f"- generated_at: {now}",
        "- adoption: ADOPT_PARTIAL into existing motion_lab gait QA and improvement algorithm",
        "- legal_policy: metadata-first; direct_free downloads only; paid/unclear sources queued",
        "- scope: humanoid/biped walking, ZMP/CoM, foot contact, IK, support polygon, gait timing",
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
    lines.extend(["", "## Algorithm Rules Added", ""])
    for rule in ALGORITHM_RULES:
        lines.append(f"- **{rule['id']}**: {rule['motion_use']}")
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
        "## Motion Pipeline Use",
        "",
        "- Score generated walks with foot contact, support polygon, root/CoM smoothness, swing clearance, and IK continuity.",
        "- Use the score as an observation-first gate before automatic destructive edits.",
        "- For mecha/proportion-mismatched rigs, prefer bounded correction weights over literal humanoid dynamics.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    for rule in ALGORITHM_RULES:
        conn.execute(
            """
            INSERT INTO algorithm_rules(id, priority, metric, rule, motion_use, source_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                priority=excluded.priority,
                metric=excluded.metric,
                rule=excluded.rule,
                motion_use=excluded.motion_use,
                source_ids=excluded.source_ids
            """,
            (
                rule["id"],
                rule["priority"],
                rule["metric"],
                rule["rule"],
                rule["motion_use"],
                json.dumps(rule["source_ids"], ensure_ascii=False),
                now,
            ),
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
        (now, "robotics gait humanoid walking ZMP CoM foot contact IK", len(DIRECT_FREE_SOURCES), len(downloaded), len(failed)),
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
        "algorithm_rule_count": len(ALGORITHM_RULES),
        "downloaded": downloaded,
        "failed": failed,
        "acquisition_queue": ACQUISITION_QUEUE,
        "algorithm_rules": ALGORITHM_RULES,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "robotics_gait_algorithm_rules.json").write_text(json.dumps(ALGORITHM_RULES, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(downloaded, failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
