import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
WORKSPACE = ROOT / "data" / "workspace"
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "fleet_intelligence_knowledge.db"
PLAN_PATH = APP_DIR / "fleet_growth_compound_plan.json"
STATUS_PATHS = {
    "fleet_idle": WORKSPACE / "fleet_idle_dispatch_status.json",
    "growth_allocation": WORKSPACE / "k10_growth_allocation.json",
    "revolutionary": WORKSPACE / "fleet_revolutionary_evolution_status.json",
    "growth_stats": WORKSPACE / "apps" / "growth_dashboard" / "growth_stats.json",
}
JST = timezone(timedelta(hours=9))


NODE_CAPABILITIES = {
    "k10": ["orchestrator", "repo_write", "heavy_coordination", "security_policy", "dashboard"],
    "red_lavie": ["openradioss", "qms", "rag", "web_research", "document_parse"],
    "lavie": ["openfoam", "cae", "qms", "light_probe"],
    "thinkpad": ["fem_impact", "dxf2step", "qms", "ssh_worker", "document_parse"],
    "dynabook": ["light_probe", "dry_run", "brv_sync", "qms"],
    "lavie_i3": ["light_probe", "health_snapshot", "monitoring"],
    "g3": ["n8n", "legacy_probe"],
    "vivobook": ["daytime_light_only"],
    "hp": ["manual_review"],
}


INVESTMENTS = [
    {
        "id": "fleet_security_posture",
        "title": "Fleet security posture visibility",
        "category": "security",
        "impact": 9.0,
        "parallelism": 7.0,
        "learning": 7.0,
        "risk": 3.0,
        "preferred_capabilities": ["light_probe", "monitoring", "security_policy", "qms"],
        "safe_next_action": "Generate read-only OS/package/security posture snapshots; do not patch automatically.",
    },
    {
        "id": "distributed_test_and_benchmark",
        "title": "Distributed tests and benchmarks",
        "category": "app_development",
        "impact": 8.0,
        "parallelism": 8.0,
        "learning": 8.0,
        "risk": 2.0,
        "preferred_capabilities": ["repo_write", "dxf2step", "fem_impact", "light_probe"],
        "safe_next_action": "Split tests and benchmarks by node capability, then record duration/failure tags.",
    },
    {
        "id": "knowledge_scout_db_pipeline",
        "title": "Knowledge scout -> DB -> rule cards",
        "category": "self_evolution",
        "impact": 8.5,
        "parallelism": 6.0,
        "learning": 9.0,
        "risk": 2.0,
        "preferred_capabilities": ["web_research", "rag", "document_parse", "orchestrator"],
        "safe_next_action": "Run bounded metadata-first scouting and direct-free downloads only.",
    },
    {
        "id": "cae_north_star_gap_closure",
        "title": "North-star CAE gap closure",
        "category": "cae",
        "impact": 9.5,
        "parallelism": 4.0,
        "learning": 8.0,
        "risk": 5.0,
        "preferred_capabilities": ["openfoam", "openradioss", "fem_impact"],
        "safe_next_action": "Use existing k10_growth_allocation and tri-track CAE loops; do not create a parallel solver loop.",
    },
    {
        "id": "agent_policy_gate_hardening",
        "title": "Agent policy gate hardening",
        "category": "safety",
        "impact": 8.0,
        "parallelism": 5.0,
        "learning": 6.5,
        "risk": 2.0,
        "preferred_capabilities": ["security_policy", "orchestrator", "qms"],
        "safe_next_action": "Convert repeated incident lessons into policy-as-code checks and dry-run gates.",
    },
    {
        "id": "idle_work_stealing_backlog",
        "title": "Bounded idle work-stealing backlog",
        "category": "utilization",
        "impact": 7.0,
        "parallelism": 8.0,
        "learning": 6.0,
        "risk": 3.0,
        "preferred_capabilities": ["light_probe", "web_research", "document_parse", "qms"],
        "safe_next_action": "Let idle nodes pull only low-risk read-only jobs from a capped backlog.",
    },
]


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def node_health_from_idle(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    cycle = status.get("last_cycle") or {}
    for item in cycle.get("node_results") or []:
        node_id = str(item.get("node_id") or item.get("registry_id") or "").lower()
        if not node_id:
            continue
        decision = str(item.get("decision") or "unknown")
        reason = str(item.get("reason") or "")
        metrics = item.get("metrics_snapshot") or {}
        availability = 0.5
        if decision == "dispatch":
            availability = 1.0
        elif "thermal" in reason.lower():
            availability = 0.25
        elif "cpu" in reason.lower() or "ram" in reason.lower():
            availability = 0.35
        elif decision == "error":
            availability = 0.1
        elif decision == "skip":
            availability = 0.4
        out[node_id] = {
            "decision": decision,
            "reason": reason,
            "metrics": metrics,
            "availability": availability,
            "capabilities": NODE_CAPABILITIES.get(node_id, ["unknown"]),
        }
    return out


def collect_nodes() -> dict[str, dict[str, Any]]:
    idle = read_json(STATUS_PATHS["fleet_idle"])
    nodes = node_health_from_idle(idle)
    for node_id, caps in NODE_CAPABILITIES.items():
        nodes.setdefault(
            node_id,
            {
                "decision": "not_seen_current_cycle",
                "reason": "no current metrics in fleet_idle_dispatch_status",
                "metrics": {},
                "availability": 0.2 if node_id not in {"k10"} else 0.8,
                "capabilities": caps,
            },
        )
    return nodes


def read_growth_pressure() -> dict[str, Any]:
    allocation = read_json(STATUS_PATHS["growth_allocation"])
    stats = read_json(STATUS_PATHS["growth_stats"])
    ranked = allocation.get("ranked_domains") or []
    top = ranked[:5]
    avg_priority = 0.0
    if top:
        avg_priority = sum(float(item.get("priority_score") or 0) for item in top) / len(top)
    dxf_success = ((stats.get("dxf2step_summary") or {}).get("success_rate_pct"))
    return {
        "top_domains": [str(item.get("domain") or "") for item in top],
        "avg_top_priority": round(avg_priority, 3),
        "dxf2step_success_pct": dxf_success,
        "stats_updated_at": stats.get("updated_at"),
    }


def source_rule_count() -> dict[str, int]:
    if not DB_PATH.exists():
        return {"sources": 0, "rules": 0}
    conn = sqlite3.connect(DB_PATH)
    try:
        return {
            "sources": int(conn.execute("select count(*) from sources where status='downloaded'").fetchone()[0]),
            "rules": int(conn.execute("select count(*) from algorithm_rules").fetchone()[0]),
        }
    except Exception:
        return {"sources": 0, "rules": 0}
    finally:
        conn.close()


def write_plan_history(plan: dict[str, Any]) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_history (
                plan_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                top_investment_id TEXT,
                top_title TEXT,
                verdict TEXT NOT NULL,
                plan_json TEXT NOT NULL
            )
            """
        )
        rec = plan.get("recommended_next_action") or {}
        plan_id = "fleet-growth-plan-" + datetime.now(JST).strftime("%Y%m%dT%H%M%S%z")
        conn.execute(
            """
            INSERT OR REPLACE INTO plan_history
            (plan_id, created_at, top_investment_id, top_title, verdict, plan_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                plan.get("updated_at") or now_iso(),
                rec.get("investment_id"),
                rec.get("title"),
                rec.get("verdict") or "PROPOSE_ONLY",
                json.dumps(plan, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def node_fit(investment: dict[str, Any], node: dict[str, Any]) -> float:
    caps = set(node.get("capabilities") or [])
    preferred = set(investment.get("preferred_capabilities") or [])
    if not preferred:
        return 0.0
    match = len(caps & preferred) / max(len(preferred), 1)
    return match * float(node.get("availability") or 0.0)


def score_investment(investment: dict[str, Any], nodes: dict[str, dict[str, Any]], pressure: dict[str, Any]) -> dict[str, Any]:
    fits = []
    for node_id, node in nodes.items():
        fit = node_fit(investment, node)
        if fit > 0:
            fits.append({"node": node_id, "fit": round(fit, 3), "reason": node.get("reason"), "decision": node.get("decision")})
    fits.sort(key=lambda item: item["fit"], reverse=True)
    usable_parallelism = sum(item["fit"] for item in fits[:4])
    growth_pressure = min(2.0, float(pressure.get("avg_top_priority") or 0.0) / 10.0)
    score = (
        float(investment["impact"]) * 1.8
        + float(investment["parallelism"]) * usable_parallelism
        + float(investment["learning"]) * 1.4
        + growth_pressure
        - float(investment["risk"]) * 1.7
    )
    no_go: list[str] = []
    if investment["category"] == "cae" and usable_parallelism < 0.5:
        no_go.append("Not enough current CAE node headroom; use existing CAE loops only.")
    if investment["category"] == "security":
        no_go.append("Read-only posture collection first; no automatic patching.")
    return {
        **investment,
        "compound_score": round(score, 3),
        "recommended_nodes": fits[:4],
        "usable_parallelism": round(usable_parallelism, 3),
        "no_go": no_go,
    }


def build_plan() -> dict[str, Any]:
    nodes = collect_nodes()
    pressure = read_growth_pressure()
    knowledge = source_rule_count()
    ranked = [score_investment(item, nodes, pressure) for item in INVESTMENTS]
    ranked.sort(key=lambda item: item["compound_score"], reverse=True)
    top = ranked[0] if ranked else {}
    return {
        "schema": "clawstack.fleet_growth_compound_plan.v1",
        "updated_at": now_iso(),
        "adoption": "ADOPT_PARTIAL_READ_ONLY",
        "non_duplication": {
            "uses_existing": [
                "scripts/k10_fleet_idle_dispatch.py",
                "scripts/k10_growth_allocation.py",
                "scripts/fleet_revolutionary_evolution_loop.py",
            ],
            "does_not_replace": True,
            "does_not_execute_jobs": True,
        },
        "growth_model": {
            "target": "compound/exponential-like improvement through reusable capability gains",
            "guardrail": "No unbounded self-modification; every execution remains gated by evidence, tests, rollback, and approval.",
            "score_terms": ["impact", "parallelism", "learning", "growth_pressure", "risk"],
        },
        "knowledge_db": knowledge,
        "growth_pressure": pressure,
        "node_snapshot": nodes,
        "ranked_investments": ranked,
        "recommended_next_action": {
            "investment_id": top.get("id"),
            "title": top.get("title"),
            "action": top.get("safe_next_action"),
            "nodes": top.get("recommended_nodes", []),
            "verdict": "PROPOSE_ONLY",
        },
        "strict_no_go": [
            "Do not modify docker-compose or core routing from this planner.",
            "Do not auto-patch OS or dependencies without an approved plan.",
            "Do not send company-file-server credentials or direct company access to K10.",
            "Do not run infinite self-improvement loops; every loop needs bounds and status output.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate read-only K10 fleet compound growth plan.")
    parser.add_argument("--out", type=Path, default=PLAN_PATH)
    args = parser.parse_args()
    plan = build_plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_plan_history(plan)
    print(json.dumps(plan["recommended_next_action"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
