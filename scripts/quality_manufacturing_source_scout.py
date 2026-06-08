import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
OUT_JSON = WORKSPACE / "quality_manufacturing_source_scout_status.json"
OUT_MD = WORKSPACE / "quality_manufacturing_source_scout_status.md"
JST = timezone(timedelta(hours=9))


SOURCES: list[dict[str, Any]] = [
    {
        "name": "NIST/SEMATECH Engineering Statistics Handbook",
        "url": "https://www.nist.gov/programs-projects/nistsematech-engineering-statistics-handbook",
        "cost_label": "FREE",
        "source_type": "official_handbook",
        "domains": ["spc", "sqc", "doe", "msa", "process_capability", "quality_management"],
        "priority": 1,
        "why": "Strong free baseline for SPC, DOE, process monitoring, measurement, and statistical quality thinking.",
        "next_query": "site:nist.gov SEMATECH engineering statistics handbook SPC MSA DOE process capability",
    },
    {
        "name": "AIAG Quality Core Tools",
        "url": "https://www.aiag.org/expertise-areas/quality/quality-core-tools",
        "cost_label": "PAID",
        "source_type": "official_standards_and_training",
        "domains": ["apqp", "control_plan", "ppap", "fmea", "msa", "spc", "iatf"],
        "priority": 1,
        "why": "Authoritative source for automotive core tools. Many manuals and courses are paid, so use as paid-reference candidate.",
        "next_query": "site:aiag.org APQP Control Plan PPAP FMEA MSA SPC free overview",
    },
    {
        "name": "AIAG Core Tools Key Terms and Self Assessment",
        "url": "https://go.aiag.org/core-tools-terms",
        "cost_label": "FREE_REG",
        "source_type": "official_reference",
        "domains": ["apqp", "fmea", "msa", "spc", "ppap", "training"],
        "priority": 2,
        "why": "Useful free or registration-gated glossary/self-assessment entry point before buying manuals.",
        "next_query": "AIAG core tools terms self assessment APQP FMEA MSA SPC",
    },
    {
        "name": "NASA Systems Engineering Handbook",
        "url": "https://www.nasa.gov/reference/systems-engineering-handbook/",
        "cost_label": "FREE",
        "source_type": "official_handbook",
        "domains": ["requirements", "risk", "verification", "fmea", "systems_engineering", "project_management"],
        "priority": 1,
        "why": "Good free framework for requirements, validation, verification, risk, interfaces, and complex app development discipline.",
        "next_query": "NASA systems engineering handbook risk requirements verification FMEA PDF",
    },
    {
        "name": "NASA Technical Reports Server",
        "url": "https://ntrs.nasa.gov/",
        "cost_label": "FREE",
        "source_type": "official_repository",
        "domains": ["risk", "failure_analysis", "simulation", "materials", "systems_engineering"],
        "priority": 2,
        "why": "Large technical-report repository for failure analysis, verification, modelling, and engineering methods.",
        "next_query": "site:ntrs.nasa.gov FMEA risk management verification manufacturing simulation",
    },
    {
        "name": "Autodesk Moldflow Insight Help",
        "url": "https://help.autodesk.com/view/MFIA/2026/ENU/",
        "cost_label": "FREE",
        "source_type": "official_help",
        "domains": ["injection_molding", "moldflow", "resin_flow", "warpage", "cooling", "materials"],
        "priority": 1,
        "why": "Best legitimate reference for Moldflow result terminology and benchmark interpretation.",
        "next_query": "site:help.autodesk.com/view/MFIA injection molding filling packing cooling warpage material model",
    },
    {
        "name": "openInjMoldSim Paper",
        "url": "https://www.mdpi.com/2311-5521/5/2/84",
        "cost_label": "FREE",
        "source_type": "open_access_paper",
        "domains": ["injection_molding", "openfoam", "resin_flow", "vof", "non_newtonian", "solver_design"],
        "priority": 1,
        "why": "Closest open paper pattern for building our own injection molding simulation and using Moldflow as benchmark.",
        "next_query": "openInjMoldSim OpenFOAM injection molding Cross WLF Tait VOF",
    },
    {
        "name": "OpenFOAM Documentation",
        "url": "https://www.openfoam.com/documentation/overview",
        "cost_label": "FREE",
        "source_type": "official_docs",
        "domains": ["cfd", "openfoam", "mesh", "solver_design", "post_processing"],
        "priority": 1,
        "why": "Free CFD solver docs for file structure, meshing, numerical schemes, and post-processing foundations.",
        "next_query": "OpenFOAM user guide multiphase non Newtonian polymer injection molding",
    },
    {
        "name": "OpenRadioss Documentation",
        "url": "https://openradioss.atlassian.net/wiki/spaces/OPENRADIOSS/overview",
        "cost_label": "FREE",
        "source_type": "official_docs",
        "domains": ["openradioss", "explicit_dynamics", "press_forming", "bending", "blanking", "springback"],
        "priority": 1,
        "why": "Primary reference for our bending and blanking solver work and deck correctness.",
        "next_query": "OpenRadioss examples shell forming bending blanking springback",
    },
    {
        "name": "MVTec Anomaly Detection Datasets",
        "url": "https://www.mvtec.com/company/research/datasets",
        "cost_label": "FREE_REG",
        "source_type": "official_dataset",
        "domains": ["visual_inspection", "anomaly_detection", "dataset", "deep_learning"],
        "priority": 1,
        "why": "Standard benchmark family for industrial anomaly detection. License is typically non-commercial, so confirm before business use.",
        "next_query": "MVTec AD dataset license anomaly detection industrial inspection",
    },
    {
        "name": "Kolektor Surface-Defect Dataset",
        "url": "https://www.vicos.si/resources/kolektorsdd",
        "cost_label": "FREE_REG",
        "source_type": "academic_dataset",
        "domains": ["visual_inspection", "surface_defect", "segmentation", "deep_learning"],
        "priority": 1,
        "why": "Real industrial surface-defect dataset with annotations, useful for small-defect segmentation experiments.",
        "next_query": "KolektorSDD Kolektor surface defect dataset license paper",
    },
    {
        "name": "CVF Open Access",
        "url": "https://openaccess.thecvf.com/",
        "cost_label": "FREE",
        "source_type": "open_access_papers",
        "domains": ["computer_vision", "visual_inspection", "anomaly_detection", "segmentation", "3d_generation"],
        "priority": 1,
        "why": "Reliable open papers for CVPR/ICCV/ECCV methods, often with code links.",
        "next_query": "site:openaccess.thecvf.com industrial anomaly detection manufacturing defect segmentation",
    },
    {
        "name": "arXiv",
        "url": "https://arxiv.org/",
        "cost_label": "FREE",
        "source_type": "preprint_repository",
        "domains": ["deep_learning", "visual_inspection", "cae", "tolerance_analysis", "3d_generation"],
        "priority": 1,
        "why": "Fastest source for new theory, surveys, and implementation papers. Needs quality filtering.",
        "next_query": "arXiv industrial visual inspection survey manufacturing defect detection tolerance analysis injection molding simulation",
    },
    {
        "name": "Papers with Code",
        "url": "https://paperswithcode.com/",
        "cost_label": "FREE",
        "source_type": "paper_code_index",
        "domains": ["deep_learning", "benchmarks", "datasets", "implementation"],
        "priority": 1,
        "why": "Good for finding papers with code and benchmark tables before investing implementation time.",
        "next_query": "Papers with Code industrial anomaly detection MVTec AD VisA BTAD Real-IAD",
    },
    {
        "name": "Kaggle Datasets and Competitions",
        "url": "https://www.kaggle.com/datasets",
        "cost_label": "FREE_REG",
        "source_type": "dataset_platform",
        "domains": ["visual_inspection", "predictive_maintenance", "process_data", "deep_learning"],
        "priority": 2,
        "why": "Useful datasets such as Severstal steel defects and predictive maintenance examples. Registration and license checks required.",
        "next_query": "site:kaggle.com manufacturing defect detection predictive maintenance quality dataset",
    },
    {
        "name": "Roboflow Universe",
        "url": "https://universe.roboflow.com/",
        "cost_label": "FREE_REG",
        "source_type": "dataset_model_platform",
        "domains": ["visual_inspection", "object_detection", "segmentation", "dataset_management"],
        "priority": 2,
        "why": "Large public CV dataset catalog. Quality varies, so use as candidate source, not ground truth.",
        "next_query": "Roboflow Universe manufacturing defect detection surface scratch dataset license",
    },
    {
        "name": "Zenodo",
        "url": "https://zenodo.org/",
        "cost_label": "FREE",
        "source_type": "research_data_repository",
        "domains": ["datasets", "papers", "cae", "manufacturing", "quality"],
        "priority": 2,
        "why": "Good for DOI-backed datasets and supplementary material with explicit licenses.",
        "next_query": "site:zenodo.org manufacturing defect dataset sheet metal forming injection molding tolerance analysis",
    },
    {
        "name": "Figshare",
        "url": "https://figshare.com/",
        "cost_label": "FREE",
        "source_type": "research_data_repository",
        "domains": ["datasets", "materials", "inspection", "cae"],
        "priority": 3,
        "why": "Supplementary datasets with DOI and license metadata; useful after core sources.",
        "next_query": "site:figshare.com manufacturing defect inspection dataset forming simulation",
    },
    {
        "name": "Mendeley Data",
        "url": "https://data.mendeley.com/",
        "cost_label": "FREE",
        "source_type": "research_data_repository",
        "domains": ["datasets", "inspection", "predictive_maintenance", "materials"],
        "priority": 3,
        "why": "Often hosts dataset companions to engineering papers.",
        "next_query": "site:data.mendeley.com manufacturing defect detection predictive maintenance dataset",
    },
    {
        "name": "PubMed Central",
        "url": "https://pmc.ncbi.nlm.nih.gov/",
        "cost_label": "FREE",
        "source_type": "open_access_papers",
        "domains": ["statistics", "machine_learning", "measurement", "quality"],
        "priority": 3,
        "why": "Not manufacturing-specific, but strong for statistics, validation, and ML evaluation methods.",
        "next_query": "site:pmc.ncbi.nlm.nih.gov machine learning anomaly detection measurement validation statistical process control",
    },
    {
        "name": "DOAJ",
        "url": "https://doaj.org/",
        "cost_label": "FREE",
        "source_type": "open_access_index",
        "domains": ["open_access", "manufacturing", "quality", "cae"],
        "priority": 3,
        "why": "Open access journal index useful for screening non-paywalled engineering articles.",
        "next_query": "DOAJ sheet metal forming injection molding simulation quality management manufacturing",
    },
    {
        "name": "J-STAGE",
        "url": "https://www.jstage.jst.go.jp/",
        "cost_label": "FREE",
        "source_type": "japanese_open_papers",
        "domains": ["japanese", "manufacturing", "quality", "materials", "forming"],
        "priority": 2,
        "why": "Japanese technical papers and society journals; useful for Japanese manufacturing terminology and practical framing.",
        "next_query": "site:jstage.jst.go.jp resin flow analysis press forming tolerance analysis visual inspection deep learning",
    },
    {
        "name": "AIST Research and DB",
        "url": "https://www.aist.go.jp/",
        "cost_label": "FREE",
        "source_type": "official_research",
        "domains": ["japanese", "manufacturing", "ai", "metrology", "materials"],
        "priority": 3,
        "why": "Japanese industrial AI, measurement, materials, and manufacturing research gateway.",
        "next_query": "site:aist.go.jp manufacturing AI visual inspection metrology materials dataset",
    },
    {
        "name": "IPA Digital Skill and DX Materials",
        "url": "https://www.ipa.go.jp/",
        "cost_label": "FREE",
        "source_type": "official_guidance",
        "domains": ["dx", "security", "ai_governance", "training", "software_quality"],
        "priority": 3,
        "why": "Useful for internal training apps, IT governance, security, and DX skill maps.",
        "next_query": "site:ipa.go.jp AI quality DX skills security training material",
    },
    {
        "name": "ISO, JIS, IATF Standard Texts",
        "url": "https://www.iso.org/standards.html",
        "cost_label": "PAID",
        "source_type": "standards",
        "domains": ["iatf", "iso", "jis", "audit", "qms"],
        "priority": 1,
        "why": "Authoritative, but usually paid and license-restricted. Do not download from unofficial mirrors.",
        "next_query": "ISO 9001 IATF 16949 internal audit guidance official paid standard",
    },
    {
        "name": "SAE Mobilus",
        "url": "https://saemobilus.sae.org/",
        "cost_label": "PAID",
        "source_type": "technical_papers",
        "domains": ["automotive", "manufacturing", "cae", "materials", "quality"],
        "priority": 3,
        "why": "Can contain high-value automotive manufacturing papers, but usually paid.",
        "next_query": "SAE sheet metal forming tolerance analysis injection molding quality manufacturing",
    },
    {
        "name": "IEEE Xplore",
        "url": "https://ieeexplore.ieee.org/",
        "cost_label": "PAID",
        "source_type": "technical_papers",
        "domains": ["deep_learning", "visual_inspection", "factory_ai", "sensors"],
        "priority": 3,
        "why": "Good for sensor/vision/AI papers, but many articles are paid. Prefer arXiv/CVF copy when available.",
        "next_query": "IEEE industrial visual inspection deep learning manufacturing defect detection",
    },
]


DOMAIN_LABELS = {
    "qms_core_tools": ["iatf", "apqp", "control_plan", "ppap", "fmea", "msa", "spc", "quality_management"],
    "visual_inspection_ai": ["visual_inspection", "anomaly_detection", "surface_defect", "deep_learning", "computer_vision"],
    "resin_flow_moldflow": ["injection_molding", "moldflow", "resin_flow", "openfoam", "vof"],
    "press_progressive_die": ["openradioss", "press_forming", "bending", "blanking", "springback"],
    "tolerance_cetol_like": ["tolerance_analysis", "process_capability", "msa", "statistics"],
    "training_video_and_dx": ["training", "3d_generation", "dx", "software_quality", "ai_governance"],
}


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def check_url(url: str, timeout: int = 10) -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 ClawstackQualityScout/1.0",
        "Accept": "text/html,application/pdf,application/json,*/*",
    }
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="HEAD", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": 200 <= int(resp.status) < 400,
                "status": int(resp.status),
                "elapsed_ms": elapsed_ms,
                "content_type": resp.headers.get("content-type", ""),
            }
    except urllib.error.HTTPError as exc:
        if int(exc.code) in {403, 405, 429}:
            return check_url_get(url, started, headers, timeout)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": 200 <= int(exc.code) < 400,
            "status": int(exc.code),
            "elapsed_ms": elapsed_ms,
            "error": str(exc)[:200],
        }
    except Exception as exc:
        fallback = check_url_get(url, started, headers, timeout)
        if fallback.get("ok"):
            return fallback
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": str(exc)[:200], "fallback": fallback}


def check_url_get(url: str, started: float, headers: dict[str, str], timeout: int) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={**headers, "Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(1024)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": 200 <= int(resp.status) < 400,
                "status": int(resp.status),
                "elapsed_ms": elapsed_ms,
                "content_type": resp.headers.get("content-type", ""),
                "method": "GET_RANGE",
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": 200 <= int(exc.code) < 400,
            "status": int(exc.code),
            "elapsed_ms": elapsed_ms,
            "error": str(exc)[:200],
            "method": "GET_RANGE",
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "elapsed_ms": elapsed_ms, "error": str(exc)[:200], "method": "GET_RANGE"}


def group_sources(sources: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in DOMAIN_LABELS}
    for source in sources:
        domains = set(source.get("domains", []))
        for label, terms in DOMAIN_LABELS.items():
            if domains.intersection(terms):
                grouped[label].append(source)
    for label in grouped:
        grouped[label].sort(key=lambda row: (int(row.get("priority", 9)), row.get("cost_label", "ZZZ"), row["name"]))
    return grouped


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Quality Manufacturing Source Scout",
        "",
        f"- Updated: {payload['updated_at']}",
        f"- Mode: {payload['mode']}",
        f"- Source count: {len(payload['sources'])}",
        "- Reachability checks are advisory; a failed check can mean bot protection, HEAD blocking, or a local network timeout.",
        "",
        "## Safety Policy",
        "",
        "- Prefer FREE and official/open-access sources first.",
        "- Do not bypass paywalls, DRM, login walls, or license controls.",
        "- Mark paid standards, paid manuals, and paid databases as PAID before use.",
        "- Treat unknown mirrors and unofficial PDFs as CHECK until the origin is verified.",
        "- Download large datasets only after license and storage impact are confirmed.",
        "",
        "## Cost Labels",
        "",
        "- FREE: Free and normally accessible.",
        "- FREE_REG: Free or open, but registration, license acceptance, API key, or non-commercial terms may apply.",
        "- PAID: Purchase, subscription, membership, or paid database access is likely.",
        "- CHECK: Copyright, redistribution, or source legitimacy needs review.",
        "",
        "## Recommended First Reading",
        "",
    ]
    for row in payload["recommended_first_reading"]:
        lines.append(f"- {row['cost_label']} P{row['priority']} [{row['name']}]({row['url']})")
        lines.append(f"  - {row['why']}")
    lines.extend(["", "## Domain Map", ""])
    for domain, rows in payload["grouped_sources"].items():
        lines.append(f"### {domain}")
        for row in rows:
            status = row.get("reachability", {})
            check = ""
            if status:
                check = f" status={status.get('status', 'n/a')} ok={status.get('ok')}"
            lines.append(f"- {row['cost_label']} P{row['priority']} [{row['name']}]({row['url']}){check}")
            lines.append(f"  - {row['why']}")
            lines.append(f"  - scout query: `{row['next_query']}`")
        lines.append("")
    lines.extend(["## Paid Watchlist", ""])
    for row in payload["paid_watchlist"]:
        lines.append(f"- PAID [{row['name']}]({row['url']})")
        lines.append(f"  - {row['why']}")
    lines.extend(["", "## Next Actions", ""])
    for action in payload["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def build_payload(check_reachability: bool, max_checks: int) -> dict[str, Any]:
    sources = [dict(row) for row in SOURCES]
    if check_reachability:
        for idx, source in enumerate(sources):
            if idx >= max_checks:
                break
            source["reachability"] = check_url(source["url"])
            time.sleep(0.4)
    grouped = group_sources(sources)
    recommended = sorted(
        [row for row in sources if row["priority"] == 1],
        key=lambda row: (row["cost_label"] == "PAID", row["cost_label"], row["name"]),
    )
    paid = sorted([row for row in sources if row["cost_label"] == "PAID"], key=lambda row: (row["priority"], row["name"]))
    return {
        "schema": "clawstack.quality_manufacturing_source_scout.v1",
        "updated_at": now_iso(),
        "mode": "metadata_only_reachability" if check_reachability else "metadata_only",
        "sources": sources,
        "grouped_sources": grouped,
        "recommended_first_reading": recommended,
        "paid_watchlist": paid,
        "next_actions": [
            "Read NIST statistics handbook sections for SPC, DOE, process monitoring, and measurement foundations.",
            "Use Autodesk Moldflow Help plus openInjMoldSim paper to define resin-flow solver benchmark terminology.",
            "Use OpenRadioss and existing project pregates for press bending/blanking deck improvement.",
            "Use MVTec/Kolektor/CVF/arXiv/Papers with Code for visual inspection AI experiments after license checks.",
            "Treat AIAG/ISO/IATF/SAE/IEEE as paid candidates and ask before purchase or subscription use.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe source scout for manufacturing, quality, CAE, and inspection work.")
    parser.add_argument("--check-reachability", action="store_true", help="Check source URL reachability with bounded HEAD requests.")
    parser.add_argument("--max-checks", type=int, default=12, help="Maximum URLs to check when reachability is enabled.")
    args = parser.parse_args()

    payload = build_payload(args.check_reachability, max(0, args.max_checks))
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(f"[OK] wrote {OUT_JSON}")
    print(f"[OK] wrote {OUT_MD}")
    print(f"[OK] source_count={len(payload['sources'])} paid_count={len(payload['paid_watchlist'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
