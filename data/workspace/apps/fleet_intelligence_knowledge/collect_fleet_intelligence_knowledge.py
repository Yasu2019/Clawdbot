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
DB_PATH = APP_DIR / "fleet_intelligence_knowledge.db"
STATUS_PATH = APP_DIR / "fleet_intelligence_knowledge_status.json"
REPORT_PATH = APP_DIR / "fleet_intelligence_knowledge_report.md"
RULES_PATH = APP_DIR / "fleet_intelligence_rules.json"


SOURCES = [
    {
        "source_id": "ray_scheduling_official",
        "title": "Ray Core Scheduling",
        "publisher": "Ray Documentation",
        "url": "https://docs.ray.io/en/latest/ray-core/scheduling/index.html",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Locality-aware and load-aware scheduling for distributed Python tasks.",
        "local_name": "ray_scheduling_official.html",
    },
    {
        "source_id": "nomad_advanced_job_scheduling",
        "title": "Advanced job scheduling",
        "publisher": "HashiCorp Nomad Documentation",
        "url": "https://developer.hashicorp.com/nomad/docs/job-scheduling",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Bin-packing, affinity, and spread concepts for heterogeneous task placement.",
        "local_name": "nomad_advanced_job_scheduling.html",
    },
    {
        "source_id": "buildbot_workers_official",
        "title": "Buildbot Workers",
        "publisher": "Buildbot Documentation",
        "url": "https://docs.buildbot.net/current/manual/configuration/workers.html",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Master/worker pattern for distributed build and test execution.",
        "local_name": "buildbot_workers_official.html",
    },
    {
        "source_id": "buildbot_schedulers_official",
        "title": "Buildbot Schedulers",
        "publisher": "Buildbot Documentation",
        "url": "https://docs.buildbot.net/current/manual/configuration/schedulers.html",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Scheduler and worker choice patterns for staged build/test pipelines.",
        "local_name": "buildbot_schedulers_official.html",
    },
    {
        "source_id": "adaptive_async_work_stealing_arxiv_2024",
        "title": "Adaptive Asynchronous Work-Stealing for Distributed Load-Balancing",
        "publisher": "arXiv",
        "url": "https://arxiv.org/pdf/2401.04494",
        "access_label": "direct_free",
        "license_label": "open_access_pdf",
        "kind": "pdf",
        "usefulness": "Work-stealing as a fallback when central scheduling leaves nodes idle.",
        "local_name": "adaptive_async_work_stealing_arxiv_2024.pdf",
    },
    {
        "source_id": "heterogeneous_multiagent_task_allocation_oaepublish_2023",
        "title": "Heterogeneous multi-agent task allocation based on graph neural networks and ant colony optimization",
        "publisher": "OAE Publishing",
        "url": "https://www.oaepublish.com/articles/ir.2023.33",
        "access_label": "direct_free",
        "license_label": "open_access_article",
        "kind": "html",
        "usefulness": "Capability-aware allocation for heterogeneous agents with optimization-oriented scoring.",
        "local_name": "heterogeneous_multiagent_task_allocation_oaepublish_2023.html",
    },
    {
        "source_id": "self_adaptive_llm_multiagent_arxiv_2023",
        "title": "Self-Adaptive LLM-Based Multiagent Systems",
        "publisher": "arXiv",
        "url": "https://arxiv.org/pdf/2307.06187",
        "access_label": "direct_free",
        "license_label": "open_access_pdf",
        "kind": "pdf",
        "usefulness": "MAPE-K style self-adaptive agents and boundaries between reasoning and execution.",
        "local_name": "self_adaptive_llm_multiagent_arxiv_2023.pdf",
    },
    {
        "source_id": "openssf_scorecard_official",
        "title": "OpenSSF Scorecard",
        "publisher": "OpenSSF",
        "url": "https://scorecard.dev/",
        "access_label": "direct_free",
        "license_label": "official_project_site",
        "kind": "html",
        "usefulness": "Automated dependency and project security posture scoring.",
        "local_name": "openssf_scorecard_official.html",
    },
    {
        "source_id": "first_epss_official",
        "title": "Exploit Prediction Scoring System",
        "publisher": "FIRST",
        "url": "https://www.first.org/epss/",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Risk-based vulnerability prioritization by predicted exploit probability.",
        "local_name": "first_epss_official.html",
    },
    {
        "source_id": "first_cvss_v4_official",
        "title": "CVSS v4.0 Specification Document",
        "publisher": "FIRST",
        "url": "https://www.first.org/cvss/specification-document",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Severity scoring foundation for fleet vulnerability triage.",
        "local_name": "first_cvss_v4_official.html",
    },
    {
        "source_id": "opa_docs_official",
        "title": "Open Policy Agent Documentation",
        "publisher": "Open Policy Agent",
        "url": "https://openpolicyagent.org/docs",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Policy-as-code enforcement for autonomous agent and CI/CD guardrails.",
        "local_name": "opa_docs_official.html",
    },
    {
        "source_id": "fleetdm_rest_api_official",
        "title": "Fleet REST API",
        "publisher": "Fleet Device Management",
        "url": "https://fleetdm.com/docs/rest-api",
        "access_label": "direct_free",
        "license_label": "official_docs",
        "kind": "html",
        "usefulness": "Fleet device management API patterns for endpoint inventory and policy reporting.",
        "local_name": "fleetdm_rest_api_official.html",
    },
]


QUEUE = [
    {
        "title": "Commercial agent orchestration products",
        "url": "various",
        "access_label": "manual_review",
        "next_action": "Use only as architecture inspiration; avoid vendor lock-in and verify against local privacy/cost rules.",
    },
    {
        "title": "GitHub autonomous agent frameworks",
        "url": "https://github.com/",
        "access_label": "manual_review",
        "next_action": "Review license, security posture, and sandbox model before cloning or executing.",
    },
    {
        "title": "FleetDM/osquery deployment",
        "url": "https://fleetdm.com/",
        "access_label": "manual_review",
        "next_action": "Treat as design candidate only; deployment would require a separate approved implementation plan.",
    },
    {
        "title": "Cranfield multi-agent task allocation survey",
        "url": "https://dspace.lib.cranfield.ac.uk/bitstreams/1fa66dee-0793-45e5-98cd-7a0692ba2abf/download",
        "access_label": "manual_review",
        "next_action": "Automatic request returned a bot-check page; review manually before download or citation.",
    },
]


RULES = [
    {
        "rule_id": "meta_layer_no_replacement",
        "name": "Meta layer only",
        "raw_fact": "Existing project already has idle dispatch, growth allocation, and recovery loops.",
        "implementation_recommendation": "Generate plans from their outputs; do not replace or duplicate those loops.",
    },
    {
        "rule_id": "compound_growth_score",
        "name": "Compound growth scoring",
        "raw_fact": "Fleet productivity grows fastest when reusable capability improvements unlock many future tasks.",
        "implementation_recommendation": "Prioritize tasks with high impact, high parallelism, high learning value, and low safety risk.",
    },
    {
        "rule_id": "heterogeneous_capability_matching",
        "name": "Heterogeneous capability matching",
        "raw_fact": "Distributed scheduling and multi-agent allocation assign work based on resource and capability fit.",
        "implementation_recommendation": "Match job class to node role, live resource state, thermal headroom, and historic success.",
    },
    {
        "rule_id": "work_stealing_fallback",
        "name": "Work stealing fallback",
        "raw_fact": "Work-stealing improves utilization when central planning leaves workers idle.",
        "implementation_recommendation": "Use bounded low-risk backlog pulling for idle nodes after K10 assigns protected priorities.",
    },
    {
        "rule_id": "security_as_growth_multiplier",
        "name": "Security posture as multiplier",
        "raw_fact": "Security failures erase growth gains; posture must be measured continuously.",
        "implementation_recommendation": "Score CVSS/EPSS/OpenSSF/secret risk before adopting code or sending jobs to a node.",
    },
    {
        "rule_id": "bounded_self_evolution",
        "name": "Bounded self evolution",
        "raw_fact": "Self-adaptive systems need feedback loops, but execution requires gates.",
        "implementation_recommendation": "Keep autonomous evolution in propose/dry-run mode until tests, rollback, approval, and evidence are present.",
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


def fetch_source(source: dict, timeout_sec: int, metadata_only: bool) -> dict:
    target = DOWNLOAD_DIR / source["local_name"]
    result = dict(source)
    result.update(
        {
            "status": "metadata_only" if metadata_only else "pending",
            "accessed_at": now_iso(),
            "local_path": str(target.relative_to(APP_DIR)),
            "sha256": "",
            "bytes": 0,
            "error": "",
        }
    )
    if metadata_only:
        return result
    request = Request(source["url"], headers={"User-Agent": "ClawstackFleetIntelligenceScout/1.0"})
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            data = response.read()
        lower_head = data[:4096].lower()
        if source["kind"] == "pdf" and not data.startswith(b"%PDF"):
            raise ValueError("downloaded payload is not a PDF")
        if source["kind"] == "html" and (b"not a bot" in lower_head or b"captcha" in lower_head):
            raise ValueError("downloaded payload appears to be bot-check HTML")
        target.write_bytes(data)
        result["status"] = "downloaded"
        result["bytes"] = target.stat().st_size
        result["sha256"] = sha256_file(target)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        try:
            target.unlink()
        except OSError:
            pass
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
        conn.execute("DELETE FROM acquisition_queue")
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
        for rule in RULES:
            conn.execute(
                """
                INSERT OR REPLACE INTO algorithm_rules
                (rule_id, name, raw_fact, implementation_recommendation)
                VALUES (?, ?, ?, ?)
                """,
                (rule["rule_id"], rule["name"], rule["raw_fact"], rule["implementation_recommendation"]),
            )
        for item in QUEUE:
            conn.execute(
                """
                INSERT INTO acquisition_queue (title, url, access_label, next_action, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item["title"], item["url"], item["access_label"], item["next_action"], finished_at),
            )
        conn.execute(
            """
            INSERT OR REPLACE INTO run_log
            (run_id, started_at, finished_at, downloaded_count, failed_count, queued_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                started_at,
                finished_at,
                sum(1 for item in results if item["status"] == "downloaded"),
                sum(1 for item in results if item["status"] == "download_failed"),
                len(QUEUE),
            ),
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
        "source_count": len(results),
        "downloaded_count": len(downloaded),
        "failed_count": len(failed),
        "manual_queue_count": len(QUEUE),
        "rules_count": len(RULES),
        "sources": results,
        "queue": QUEUE,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    RULES_PATH.write_text(json.dumps(RULES, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Fleet Intelligence Knowledge Scout",
        "",
        f"- run_id: `{run_id}`",
        f"- downloaded direct_free sources: `{len(downloaded)}` / `{len(results)}`",
        f"- manual/acquisition queue: `{len(QUEUE)}`",
        f"- DB: `{DB_PATH.name}`",
        "",
        "## Adoption Decision",
        "",
        "ADOPT_PARTIAL: use as read-only K10 fleet meta-planning knowledge. Do not replace existing dispatch/recovery loops.",
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
    for rule in RULES:
        lines.append(f"- `{rule['rule_id']}`: {rule['implementation_recommendation']}")
    lines.extend(["", "## Manual Review Queue", ""])
    for item in QUEUE:
        lines.append(f"- `{item['access_label']}` {item['title']}: {item['next_action']}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect fleet intelligence and compound growth sources.")
    parser.add_argument("--timeout-sec", type=int, default=45)
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    run_id = "fleet-intelligence-scout-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results = []
    for source in SOURCES:
        results.append(fetch_source(source, args.timeout_sec, args.metadata_only))
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
