import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = APP_DIR / "downloads"
DB_PATH = APP_DIR / "self_healing_system_knowledge.db"
STATUS_PATH = APP_DIR / "self_healing_system_knowledge_status.json"
REPORT_PATH = APP_DIR / "self_healing_system_knowledge_report.md"
RULES_PATH = APP_DIR / "docker_self_healing_rules.json"


SOURCES = [
    {
        "source_id": "self_healing_software_survey_arxiv_2024",
        "title": "A Survey on Self-healing Software System",
        "publisher": "arXiv",
        "url": "https://arxiv.org/pdf/2403.00455",
        "access_label": "direct_free",
        "license_label": "open_access_pdf",
        "kind": "pdf",
        "usefulness": "Broad survey of self-healing models, MAPE-K usage, failure detection, and adaptation actions.",
        "local_name": "self_healing_software_survey_arxiv_2024.pdf",
    },
    {
        "source_id": "autonomic_microservices_mapek_icsa_2022",
        "title": "A MAPE-K Approach to Autonomic Microservices",
        "publisher": "University of Bologna / ICSA Companion",
        "url": "https://www.cs.unibo.it/~lanese/newpublications/fulltext/icsa-c2022-autonomic.pdf",
        "access_label": "direct_free",
        "license_label": "author_open_pdf",
        "kind": "pdf",
        "usefulness": "Maps microservice autonomy into monitor, analyze, plan, execute, and knowledge phases.",
        "local_name": "autonomic_microservices_mapek_icsa_2022.pdf",
    },
    {
        "source_id": "self_healing_systems_frameworks_st_andrews_2013",
        "title": "A Survey of Self-Healing Systems Frameworks",
        "publisher": "University of St Andrews repository",
        "url": "https://research-repository.st-andrews.ac.uk/bitstream/10023/6026/1/schneider_2013_asurveyofselfhealingsystemsframeworks.pdf",
        "access_label": "direct_free",
        "license_label": "institutional_repository_pdf",
        "kind": "pdf",
        "usefulness": "Separates detection, diagnosis, repair, and validation patterns for self-healing systems.",
        "local_name": "self_healing_systems_frameworks_st_andrews_2013.pdf",
    },
    {
        "source_id": "kubernetes_operator_pattern_official",
        "title": "Operator pattern",
        "publisher": "Kubernetes Documentation",
        "url": "https://kubernetes.io/docs/concepts/extend-kubernetes/operator/",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Defines operators as controllers extending behavior by watching desired state and acting through APIs.",
        "local_name": "kubernetes_operator_pattern_official.html",
    },
    {
        "source_id": "kubernetes_pod_lifecycle_official",
        "title": "Pod Lifecycle",
        "publisher": "Kubernetes Documentation",
        "url": "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Official semantics for pod phases, restart behavior, probes, and container state transitions.",
        "local_name": "kubernetes_pod_lifecycle_official.html",
    },
    {
        "source_id": "cncf_operator_whitepaper",
        "title": "CNCF Operator White Paper",
        "publisher": "CNCF TAG App Delivery",
        "url": "https://tag-app-delivery.cncf.io/whitepapers/operator/",
        "access_label": "direct_free",
        "license_label": "cncf_public_web",
        "kind": "html",
        "usefulness": "Operator maturity, reconciliation, operational knowledge encoding, and human handoff boundaries.",
        "local_name": "cncf_operator_whitepaper.html",
    },
    {
        "source_id": "docker_restart_policies_official",
        "title": "Start containers automatically",
        "publisher": "Docker Docs",
        "url": "https://docs.docker.com/engine/containers/start-containers-automatically/",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Official restart policy behavior and caution against process managers inside containers.",
        "local_name": "docker_restart_policies_official.html",
    },
    {
        "source_id": "docker_compose_services_healthcheck_official",
        "title": "Compose file reference: services",
        "publisher": "Docker Docs",
        "url": "https://docs.docker.com/reference/compose-file/services/",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Official Compose service keys, including healthcheck, depends_on health conditions, and restart controls.",
        "local_name": "docker_compose_services_healthcheck_official.html",
    },
    {
        "source_id": "self_healing_systems_approaches_tuwien_2009",
        "title": "A survey on self-healing systems: approaches and systems",
        "publisher": "TU Wien distributed systems group",
        "url": "https://dsg.tuwien.ac.at/Staff/sd/papers/Zeitschrift%20Computing%20H.%20Psaier.pdf",
        "access_label": "direct_free",
        "license_label": "author_public_pdf",
        "kind": "pdf",
        "usefulness": "Classic self-healing survey covering autonomic principles, fault detection, repair, and validation.",
        "local_name": "self_healing_systems_approaches_tuwien_2009.pdf",
    },
    {
        "source_id": "self_adaptive_llm_multiagent_arxiv_2023",
        "title": "Self-Adaptive LLM-Based Multiagent Systems",
        "publisher": "arXiv",
        "url": "https://arxiv.org/pdf/2307.06187",
        "access_label": "direct_free",
        "license_label": "open_access_pdf",
        "kind": "pdf",
        "usefulness": "Useful for separating agent reasoning loops from hard execution gates in autonomous systems.",
        "local_name": "self_adaptive_llm_multiagent_arxiv_2023.pdf",
    },
]


QUEUE = [
    {
        "title": "IEEE Xplore papers on autonomic microservices and MAPE-K",
        "url": "https://ieeexplore.ieee.org/",
        "access_label": "paid_or_subscription",
        "next_action": "Acquire only through authorized institutional access or user-provided entitlement.",
    },
    {
        "title": "Docker autoheal and Watchtower GitHub projects",
        "url": "https://github.com/",
        "access_label": "manual_review",
        "next_action": "Review licenses, operational risk, and repository health before adopting any code.",
    },
    {
        "title": "Vendor blog posts about container self-healing",
        "url": "various",
        "access_label": "manual_review",
        "next_action": "Use as secondary hints only; confirm behavior against official Docker/Kubernetes docs.",
    },
    {
        "title": "Human-in-the-loop Self-adaptive Systems - Durham repository",
        "url": "https://durham-repository.worktribe.com/OutputFile/1135895",
        "access_label": "manual_review",
        "next_action": "Automatic request returned 403; review manually in browser before any download or citation.",
    },
    {
        "title": "MAPE-K Based Guidelines for Designing Reactive and Proactive Self-adaptive Systems",
        "url": "https://research.vu.nl/files/365761384/MAPE-K_Based_Guidelines_for_Designing_Reactive_and_Proactive_Self-adaptive_Systems.pdf",
        "access_label": "manual_review",
        "next_action": "Automatic request returned 403; review manually in browser before any download or citation.",
    },
]


ALGORITHM_RULES = [
    {
        "rule_id": "mapek_phase_separation",
        "name": "MAPE-K phase separation",
        "raw_fact": "Self-adaptive systems commonly separate Monitor, Analyze, Plan, Execute, and Knowledge.",
        "implementation_recommendation": "Keep this harness read-only until monitor/analyze evidence and a rollback plan exist.",
    },
    {
        "rule_id": "docker_health_is_signal_not_repair",
        "name": "Docker healthcheck is a signal",
        "raw_fact": "Docker documents health and restart controls separately; unhealthy state should be treated as evidence, not direct permission to mutate.",
        "implementation_recommendation": "Use health status to propose actions. Do not auto-restart unhealthy containers without an explicit gated executor.",
    },
    {
        "rule_id": "restart_policy_scope",
        "name": "Restart policy scope",
        "raw_fact": "Docker restart policies control behavior after container exits or daemon restarts.",
        "implementation_recommendation": "Prefer checking whether existing restart policy is appropriate before adding external restart loops.",
    },
    {
        "rule_id": "operator_reconciliation_idempotence",
        "name": "Operator-style reconciliation",
        "raw_fact": "Kubernetes operators encode operational knowledge as controllers that reconcile desired and actual state.",
        "implementation_recommendation": "Make any future executor idempotent and bounded: same input should yield the same proposed minimal action.",
    },
    {
        "rule_id": "human_in_loop_for_high_risk",
        "name": "Human approval for high-risk changes",
        "raw_fact": "Human-in-the-loop self-adaptive systems address trust and control boundaries.",
        "implementation_recommendation": "Require approval for compose edits, destructive operations, cloud spend, data deletion, or replacing stable workflows.",
    },
    {
        "rule_id": "knowledge_after_action",
        "name": "Record outcomes",
        "raw_fact": "Self-healing loops depend on a knowledge base of observations, actions, and outcomes.",
        "implementation_recommendation": "Record source, evidence, proposed action, execution result, and lesson in DB/Beads/ByteRover index cards.",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_source(source: dict, timeout_sec: int, skip_download: bool) -> dict:
    target = DOWNLOAD_DIR / source["local_name"]
    result = dict(source)
    result.update(
        {
            "status": "metadata_only" if skip_download else "pending",
            "accessed_at": now_iso(),
            "local_path": str(target.relative_to(APP_DIR)),
            "sha256": "",
            "bytes": 0,
            "error": "",
        }
    )
    if skip_download:
        return result
    if source["access_label"] != "direct_free":
        result["status"] = "queued_not_downloaded"
        return result
    request = Request(source["url"], headers={"User-Agent": "ClawstackKnowledgeScout/1.0"})
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            data = response.read()
        target.write_bytes(data)
        result["status"] = "downloaded"
        result["bytes"] = target.stat().st_size
        result["sha256"] = sha256_file(target)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        result["status"] = "download_failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            publisher TEXT NOT NULL,
            url TEXT NOT NULL,
            access_label TEXT NOT NULL,
            license_label TEXT NOT NULL,
            kind TEXT NOT NULL,
            usefulness TEXT NOT NULL,
            status TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            local_path TEXT,
            sha256 TEXT,
            bytes INTEGER,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS algorithm_rules (
            rule_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            raw_fact TEXT NOT NULL,
            implementation_recommendation TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS acquisition_queue (
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            access_label TEXT NOT NULL,
            next_action TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS run_log (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            downloaded_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            queued_count INTEGER NOT NULL
        );
        """
    )


def write_db(results: list[dict], run_id: str, started_at: str, finished_at: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM algorithm_rules")
        for item in results:
            conn.execute(
                """
                INSERT OR REPLACE INTO sources
                (source_id, title, publisher, url, access_label, license_label, kind, usefulness,
                 status, accessed_at, local_path, sha256, bytes, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["source_id"],
                    item["title"],
                    item["publisher"],
                    item["url"],
                    item["access_label"],
                    item["license_label"],
                    item["kind"],
                    item["usefulness"],
                    item["status"],
                    item["accessed_at"],
                    item["local_path"],
                    item["sha256"],
                    item["bytes"],
                    item["error"],
                ),
            )
        for rule in ALGORITHM_RULES:
            conn.execute(
                """
                INSERT OR REPLACE INTO algorithm_rules
                (rule_id, name, raw_fact, implementation_recommendation)
                VALUES (?, ?, ?, ?)
                """,
                (
                    rule["rule_id"],
                    rule["name"],
                    rule["raw_fact"],
                    rule["implementation_recommendation"],
                ),
            )
        conn.execute("DELETE FROM acquisition_queue")
        for item in QUEUE:
            conn.execute(
                """
                INSERT INTO acquisition_queue (title, url, access_label, next_action, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item["title"], item["url"], item["access_label"], item["next_action"], finished_at),
            )
        downloaded = sum(1 for item in results if item["status"] == "downloaded")
        failed = sum(1 for item in results if item["status"] == "download_failed")
        queued = len(QUEUE)
        conn.execute(
            """
            INSERT OR REPLACE INTO run_log
            (run_id, started_at, finished_at, downloaded_count, failed_count, queued_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, started_at, finished_at, downloaded, failed, queued),
        )
        conn.commit()
    finally:
        conn.close()


def write_outputs(results: list[dict], run_id: str, started_at: str, finished_at: str) -> None:
    downloaded = [item for item in results if item["status"] == "downloaded"]
    failed = [item for item in results if item["status"] == "download_failed"]
    status = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "database": str(DB_PATH.relative_to(APP_DIR)),
        "source_count": len(results),
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "manual_queue_count": len(QUEUE),
        "rules_count": len(ALGORITHM_RULES),
        "sources": results,
        "queue": QUEUE,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    RULES_PATH.write_text(json.dumps(ALGORITHM_RULES, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Docker Self-Healing Knowledge Scout",
        "",
        f"- run_id: `{run_id}`",
        f"- finished_at: `{finished_at}`",
        f"- downloaded direct_free sources: `{len(downloaded)}` / `{len(results)}`",
        f"- manual/acquisition queue: `{len(QUEUE)}`",
        f"- DB: `{DB_PATH.name}`",
        "",
        "## Adoption Decision",
        "",
        "ADOPT_PARTIAL: store knowledge and use an observation-only policy gate. Do not edit compose files or restart containers automatically from this scout.",
        "",
        "## Downloaded Sources",
        "",
    ]
    for item in results:
        mark = "[OK]" if item["status"] == "downloaded" else "[NG]"
        lines.append(f"- {mark} `{item['source_id']}` - {item['title']} ({item['access_label']}, {item['license_label']})")
        lines.append(f"  - URL: {item['url']}")
        lines.append(f"  - local: `{item['local_path']}` sha256=`{item['sha256']}` bytes=`{item['bytes']}`")
        if item["error"]:
            lines.append(f"  - error: `{item['error']}`")
    lines.extend(["", "## Algorithm Rules", ""])
    for rule in ALGORITHM_RULES:
        lines.append(f"- `{rule['rule_id']}`: {rule['implementation_recommendation']}")
    lines.extend(["", "## Manual Review Queue", ""])
    for item in QUEUE:
        lines.append(f"- `{item['access_label']}` {item['title']}: {item['next_action']}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect direct-free self-healing system knowledge.")
    parser.add_argument("--timeout-sec", type=int, default=45)
    parser.add_argument("--sleep-sec", type=float, default=0.5)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    run_id = "self-healing-scout-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = []
    for source in SOURCES:
        results.append(fetch_source(source, timeout_sec=args.timeout_sec, skip_download=args.metadata_only))
        time.sleep(args.sleep_sec)
    finished_at = now_iso()
    write_db(results, run_id, started_at, finished_at)
    write_outputs(results, run_id, started_at, finished_at)

    downloaded = sum(1 for item in results if item["status"] == "downloaded")
    failed = sum(1 for item in results if item["status"] == "download_failed")
    print(json.dumps({"run_id": run_id, "downloaded": downloaded, "failed": failed, "db": str(DB_PATH)}, ensure_ascii=False))
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
