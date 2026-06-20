import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "data" / "workspace" / "apps" / "growth_dashboard"
OUTPUT_PATH = DASHBOARD_DIR / "material_source_inventory.json"
ACQUIRED_DIR = ROOT / "data" / "web_acquired_materials"
QUEUE_PATH = DASHBOARD_DIR / "material_acquisition_queue.json"
ROBOFLOW_CANDIDATES_PATH = DASHBOARD_DIR / "roboflow_candidate_datasets.json"
MATERIALS_PROJECT_STATUS_PATH = ROOT / "data" / "workspace" / "materials_project_api_status.json"
GROWTH_DB = ROOT / "data" / "workspace" / "universal_growth.db"
HARVEST_STATUS_PATH = ROOT / "data" / "workspace" / "public_api_harvest_status.json"
PUBLIC_API_DOWNLOADS = ROOT / "data" / "public_api_downloads"
MATERIALS_PROJECT_DIR = ROOT / "data" / "cae_downloads" / "materials_project"

PUBLIC_API_SOURCE_LABELS = {
    "openalex": ("OpenAlex", "scholarly_metadata"),
    "crossref": ("Crossref", "scholarly_metadata"),
    "datacite": ("DataCite", "scholarly_metadata"),
    "europe_pmc": ("Europe PMC", "open_research_assets"),
    "semantic_scholar": ("Semantic Scholar", "scholarly_metadata"),
    "doaj": ("DOAJ", "open_research_assets"),
    "unpaywall": ("Unpaywall (OA PDF)", "open_research_assets"),
    "arxiv": ("arXiv", "open_research_assets"),
    "zenodo": ("Zenodo", "open_research_assets"),
    "figshare": ("Figshare", "open_research_assets"),
    "github": ("GitHub (API harvest)", "code_and_reference"),
    "huggingface_datasets": ("Hugging Face Datasets", "dataset_platform"),
    "ambientcg": ("AmbientCG (PBR materials)", "3d_assets"),
    "patentsview": ("USPTO PatentsView", "patent_metadata"),
    "kaggle": ("Kaggle (API harvest)", "dataset_platform"),
    "materials_project": ("Materials Project (API harvest)", "materials_database_api"),
    "roboflow": ("Roboflow (API harvest)", "vision_dataset_platform"),
    "roboflow_candidate": ("Roboflow candidates (API)", "vision_dataset_platform"),
}

DOC_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".json",
}

JST = timezone(timedelta(hours=9))


def now_jst():
    return datetime.now(JST).replace(microsecond=0).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def file_inventory(paths, name_keywords=None):
    items = []
    keywords = [k.lower() for k in (name_keywords or [])]
    for base in paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in DOC_EXTENSIONS:
                continue
            rel = path.relative_to(ROOT).as_posix()
            haystack = rel.lower()
            if keywords and not any(keyword in haystack for keyword in keywords):
                continue
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "path": rel,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).replace(microsecond=0).isoformat(),
                    "size_bytes": stat.st_size,
                }
            )
    items.sort(key=lambda item: item["modified_at"], reverse=True)
    return items


def candidate_count(source_names, patterns):
    count = 0
    examples = []
    lowered_patterns = [p.lower() for p in patterns]
    for source in source_names:
        name = str(source.get("name", ""))
        url = str(source.get("url", ""))
        text = f"{name} {url}".lower()
        if any(pattern in text for pattern in lowered_patterns):
            count += 1
            examples.append(name or url)
    return count, examples[:5]


def source_names_from_quality_scout():
    data = load_json(ROOT / "data" / "workspace" / "quality_manufacturing_source_scout_status.json", {})
    return data.get("sources", []) if isinstance(data.get("sources"), list) else []


def scout_coverage_row():
    sources = source_names_from_quality_scout()
    free_count = sum(1 for row in sources if str(row.get("cost_label", "")).upper() == "FREE")
    gated_count = sum(1 for row in sources if str(row.get("cost_label", "")).upper() in {"FREE_REG", "PAID", "CHECK"})
    examples = [
        f"{row.get('cost_label', 'CHECK')} - {row.get('name')}"
        for row in sorted(sources, key=lambda item: (int(item.get("priority", 9)), str(item.get("name", ""))))[:5]
    ]
    return {
        "source": "Broad legal source scout",
        "category": "manufacturing_research_watchlist",
        "acquired_count": 0,
        "candidate_count": len(sources),
        "status": "candidate" if sources else "not_acquired",
        "latest_at": "",
        "evidence": "quality_manufacturing_source_scout_status.json",
        "note": f"Watchlist sources: {len(sources)} total, {free_count} free, {gated_count} login/paid/check. Download is separate after license review.",
        "examples": examples,
    }


def scout_domain_row(source, category, domain_terms):
    sources = source_names_from_quality_scout()
    terms = set(domain_terms)
    matches = []
    for row in sources:
        domains = set(row.get("domains", []))
        if domains.intersection(terms):
            matches.append(row)
    matches.sort(key=lambda item: (int(item.get("priority", 9)), str(item.get("name", ""))))
    return {
        "source": source,
        "category": category,
        "acquired_count": 0,
        "candidate_count": len(matches),
        "status": "candidate" if matches else "not_acquired",
        "latest_at": "",
        "evidence": "quality_manufacturing_source_scout_status.json",
        "note": "Source candidates tracked for legal review and targeted acquisition.",
        "examples": [f"{row.get('cost_label', 'CHECK')} - {row.get('name')}" for row in matches[:5]],
    }


def scribd_row():
    scout = load_json(ROOT / "data" / "workspace" / "scribd_related_source_scout_status.json", {})
    inventory = scout.get("download_inventory", [])
    local_items = file_inventory([ROOT / "data" / "scribd_downloads"])
    if isinstance(inventory, list) and inventory:
        examples = []
        latest = ""
        for item in inventory:
            examples.append(str(item.get("name") or item.get("path") or "Scribd material"))
            modified = str(item.get("modified_at") or "")
            if modified > latest:
                latest = modified
        return {
            "source": "Scribd",
            "category": "subscription_docs",
            "acquired_count": len(inventory),
            "candidate_count": len(scout.get("candidates", [])) if isinstance(scout.get("candidates"), list) else 0,
            "status": "acquired",
            "latest_at": latest,
            "evidence": "data/scribd_downloads + scribd_related_source_scout_status.json",
            "note": f"Classified relevant downloads. Local document files: {len(local_items)}.",
            "examples": examples[:5],
        }
    return {
        "source": "Scribd",
        "category": "subscription_docs",
        "acquired_count": len(local_items),
        "candidate_count": 0,
        "status": "acquired" if local_items else "not_acquired",
        "latest_at": local_items[0]["modified_at"] if local_items else "",
        "evidence": "data/scribd_downloads",
        "note": "Counted local document files.",
        "examples": [item["name"] for item in local_items[:5]],
    }


def youtube_row():
    processed = load_json(DASHBOARD_DIR / "processed_youtube_videos.json", [])
    summary = load_json(DASHBOARD_DIR / "iatf_youtube_summary.json", [])
    transcript_items = file_inventory([ROOT / "data" / "workspace"], ["youtube_transcripts"])
    processed_count = len(processed) if isinstance(processed, list) else 0
    summary_count = len(summary) if isinstance(summary, list) else 0
    examples = [str(item) for item in processed[:5]] if isinstance(processed, list) else []
    return {
        "source": "YouTube",
        "category": "video_transcripts",
        "acquired_count": processed_count,
        "candidate_count": 0,
        "status": "acquired" if processed_count else "not_acquired",
        "latest_at": transcript_items[0]["modified_at"] if transcript_items else "",
        "evidence": "processed_youtube_videos.json / iatf_youtube_summary.json",
        "note": f"Processed video IDs: {processed_count}. Dashboard summaries: {summary_count}.",
        "examples": examples,
    }


def scout_backed_row(source, category, patterns, local_paths=None, local_keywords=None):
    sources = source_names_from_quality_scout()
    candidates, candidate_examples = candidate_count(sources, patterns)
    items = file_inventory(local_paths or [], local_keywords)
    return {
        "source": source,
        "category": category,
        "acquired_count": len(items),
        "candidate_count": 0 if items else candidates,
        "status": "acquired" if items else ("candidate" if candidates else "not_acquired"),
        "latest_at": items[0]["modified_at"] if items else "",
        "evidence": "quality_manufacturing_source_scout_status.json" if candidates else "",
        "note": "Candidate source is tracked; download/registration is still separate." if candidates and not items else "",
        "examples": [item["name"] for item in items[:5]] or candidate_examples,
    }


def roboflow_row(dataset_paths):
    data = load_json(ROBOFLOW_CANDIDATES_PATH, {})
    candidates = data.get("items", []) if isinstance(data.get("items"), list) else []
    items = file_inventory(dataset_paths, ["roboflow"])
    examples = []
    for item in candidates[:5]:
        name = str(item.get("dataset") or item.get("slug") or item.get("url") or "Roboflow dataset")
        category = str(item.get("category") or "")
        images = item.get("images")
        examples.append(f"{name} ({category}, images={images})")
    if not candidates:
        sources = source_names_from_quality_scout()
        _, examples = candidate_count(sources, ["roboflow"])
    return {
        "source": "Roboflow Universe",
        "category": "vision_dataset_platform",
        "acquired_count": len(items),
        "candidate_count": 0 if items else len(candidates),
        "status": "acquired" if items else ("candidate" if candidates else "not_acquired"),
        "latest_at": items[0]["modified_at"] if items else "",
        "evidence": ROBOFLOW_CANDIDATES_PATH.relative_to(ROOT).as_posix() if candidates else "quality_manufacturing_source_scout_status.json",
        "note": "User-registered workspace candidates. License/export review required before download." if candidates and not items else "",
        "examples": [item["name"] for item in items[:5]] or examples,
    }


def materials_project_api_row():
    status = load_json(MATERIALS_PROJECT_STATUS_PATH, {})
    api_ready = status.get("status") == "api_ready"
    local_items = file_inventory([MATERIALS_PROJECT_DIR])
    sample_materials = status.get("sample_materials", []) if isinstance(status.get("sample_materials"), list) else []
    examples = [item["name"] for item in local_items[:5]]
    if not examples:
        for row in sample_materials[:5]:
            if isinstance(row, dict):
                examples.append(f"{row.get('material_id')} {row.get('formula_pretty')} stable={row.get('is_stable')}")
    acquired = len(local_items)
    return {
        "source": "Materials Project API",
        "category": "materials_database_api",
        "acquired_count": acquired if acquired else (1 if api_ready else 0),
        "candidate_count": 0 if acquired or api_ready else 1,
        "status": "acquired" if acquired else ("api_ready" if api_ready else ("candidate" if status.get("key_present") else "not_configured")),
        "latest_at": local_items[0]["modified_at"] if local_items else status.get("updated_at", ""),
        "evidence": MATERIALS_PROJECT_DIR.relative_to(ROOT).as_posix() if local_items else MATERIALS_PROJECT_STATUS_PATH.relative_to(ROOT).as_posix(),
        "note": f"Local JSON records: {acquired}. API key configured for targeted queries." if api_ready else status.get("next_action", ""),
        "examples": examples or [status.get("status", "not_configured")],
    }


def public_api_db_rows():
    if not GROWTH_DB.exists():
        return []
    harvest_status = load_json(HARVEST_STATUS_PATH, {})
    con = sqlite3.connect(GROWTH_DB)
    downloaded_total = con.execute(
        """
        SELECT COUNT(*) FROM public_api_acquisitions
        WHERE local_path IS NOT NULL AND local_path != ''
        """
    ).fetchone()[0]
    metadata_total = con.execute(
        """
        SELECT COUNT(*) FROM public_api_acquisitions
        WHERE local_path IS NULL OR local_path = ''
        """
    ).fetchone()[0]
    stats = con.execute(
        """
        SELECT source,
               COUNT(*) AS total,
               SUM(CASE WHEN local_path IS NOT NULL AND local_path != '' THEN 1 ELSE 0 END) AS downloaded,
               MAX(acquired_at) AS latest_at
        FROM public_api_acquisitions
        GROUP BY source
        ORDER BY total DESC
        """
    ).fetchall()
    rows = []
    if harvest_status or stats:
        rows.append(
            {
                "source": "Public API bulk harvest (summary)",
                "category": "public_api_harvest",
                "acquired_count": int(downloaded_total or 0),
                "candidate_count": int(metadata_total or 0) + len(harvest_status.get("errors") or []),
                "status": "acquired" if downloaded_total else "metadata",
                "latest_at": harvest_status.get("updated_at", ""),
                "evidence": HARVEST_STATUS_PATH.relative_to(ROOT).as_posix(),
                "note": (
                    f"DB: {downloaded_total or 0} downloaded, {metadata_total or 0} metadata-only. "
                    f"Last run by_source={json.dumps(harvest_status.get('by_source') or {}, ensure_ascii=False)}. "
                    "Per-source detail rows below."
                ),
                "examples": [str(err)[:100] for err in (harvest_status.get("errors") or [])[:3]],
                "_exclude_from_totals": True,
            }
        )
    for source, total, downloaded, latest_at in stats:
        label, category = PUBLIC_API_SOURCE_LABELS.get(
            source,
            (source.replace("_", " ").title(), "public_api_harvest"),
        )
        examples = [
            (title or "item")[:100]
            for (title,) in con.execute(
                """
                SELECT title FROM public_api_acquisitions
                WHERE source = ?
                ORDER BY acquired_at DESC
                LIMIT 5
                """,
                (source,),
            ).fetchall()
        ]
        metadata_only = max(total - (downloaded or 0), 0)
        if downloaded:
            status = "acquired"
        elif "candidate" in source:
            status = "candidate"
        else:
            status = "metadata"
        rows.append(
            {
                "source": label,
                "category": category,
                "acquired_count": int(downloaded or 0),
                "candidate_count": int(metadata_only),
                "status": status,
                "latest_at": latest_at or harvest_status.get("updated_at", ""),
                "evidence": "universal_growth.db/public_api_acquisitions + public_api_harvest_status.json",
                "note": f"DB records: {total} total, {downloaded or 0} with local files. Harvest script: public_api_bulk_harvest.py.",
                "examples": examples,
            }
        )
    con.close()
    return rows


def github_download_row():
    doc_items = file_inventory([ROOT / "data" / "github_downloads"])
    zip_items = []
    base = ROOT / "data" / "github_downloads"
    if base.exists():
        for path in base.rglob("*.zip"):
            stat = path.stat()
            zip_items.append(
                {
                    "name": path.name,
                    "path": path.relative_to(ROOT).as_posix(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).replace(microsecond=0).isoformat(),
                    "size_bytes": stat.st_size,
                }
            )
        zip_items.sort(key=lambda item: item["modified_at"], reverse=True)
    all_items = sorted(doc_items + zip_items, key=lambda item: item["modified_at"], reverse=True)
    return {
        "source": "GitHub",
        "category": "code_and_reference",
        "acquired_count": len(all_items),
        "candidate_count": 0,
        "status": "acquired" if all_items else "not_acquired",
        "latest_at": all_items[0]["modified_at"] if all_items else "",
        "evidence": "data/github_downloads",
        "note": f"Local files: {len(doc_items)} docs + {len(zip_items)} zip archives.",
        "examples": [item["name"] for item in all_items[:5]],
    }


def harvest_learned_queries_row():
    path = DASHBOARD_DIR / "harvest_learned_queries.json"
    data = load_json(path, {})
    domains = data.get("domains") or {}
    examples = []
    query_count = 0
    for domain_id, payload in domains.items():
        if not isinstance(payload, dict):
            continue
        for item in payload.get("prioritized_queries") or []:
            query_count += 1
            if len(examples) < 5:
                examples.append(f"{domain_id}: {item}")
    return {
        "source": "Harvest query optimizer (learned)",
        "category": "search_efficiency",
        "acquired_count": int(data.get("scored_total") or 0),
        "candidate_count": query_count,
        "status": "active" if query_count else "pending",
        "latest_at": data.get("updated_at", ""),
        "evidence": path.relative_to(ROOT).as_posix(),
        "note": (
            "Scores downloaded/public API materials; promotes high-yield queries and similar terms first. "
            f"Domains with learned queries: {len(domains)}."
        ),
        "examples": examples,
    }


def robotics_knowledge_row():
    base = ROOT / "data" / "workspace" / "apps" / "motion_lab" / "assets" / "web_sourced" / "robotics_gait_knowledge"
    db_path = base / "robotics_gait_knowledge.db"
    status_path = base / "robotics_gait_knowledge_status.json"
    report_path = base / "robotics_gait_knowledge_report.md"
    status = load_json(status_path, {})
    examples = []
    acquired_count = int(status.get("downloaded_count") or 0)
    candidate_count = len(status.get("acquisition_queue") or [])
    latest_at = status.get("generated_at", "")
    if db_path.exists():
        try:
            con = sqlite3.connect(str(db_path))
            rows = con.execute(
                "SELECT title FROM sources WHERE status = 'downloaded' ORDER BY access_date DESC LIMIT 5"
            ).fetchall()
            examples = [row[0] for row in rows]
            con.close()
        except Exception as exc:
            examples = [f"DB read failed: {exc}"]
    return {
        "source": "Embodied robotics learning knowledge DB",
        "category": "robotics_learning",
        "acquired_count": acquired_count,
        "candidate_count": candidate_count,
        "status": "acquired" if acquired_count else "pending",
        "latest_at": latest_at,
        "evidence": report_path.relative_to(ROOT).as_posix(),
        "note": (
            "Legal web-sourced robotics knowledge for gait, household tasks, factory tasks, "
            "multi-robot learning, and edge deployment. DB: "
            f"{db_path.relative_to(ROOT).as_posix()}"
        ),
        "examples": examples,
    }


def build_inventory():
    dataset_paths = [
        ROOT / "data" / "datasets",
        ROOT / "data" / "kaggle",
        ROOT / "data" / "workspace" / "datasets",
        PUBLIC_API_DOWNLOADS / "kaggle",
    ]

    rows = [
        scout_coverage_row(),
        scribd_row(),
        youtube_row(),
        *public_api_db_rows(),
        scout_backed_row("Kaggle datasets", "dataset_platform", ["kaggle"], dataset_paths, ["kaggle"]),
        scout_backed_row("MVTec AD", "visual_inspection_dataset", ["mvtec"], dataset_paths, ["mvtec"]),
        scout_backed_row("Kolektor Surface-Defect Dataset", "visual_inspection_dataset", ["kolektor"], dataset_paths, ["kolektor"]),
        roboflow_row(dataset_paths),
        materials_project_api_row(),
        scout_domain_row("Patent idea sources", "patent_search", ["patents"]),
        scout_domain_row("CAD and standard-part sources", "cad_reference", ["cad", "3d_model", "standard_parts", "mechanical_design"]),
        scout_domain_row("Materials data sources", "materials_data", ["materials", "simulation"]),
        scout_domain_row("Video/training production sources", "training_video_sources", ["training_video", "3d_generation", "content_generation"]),
        scout_backed_row("openInjMoldSim Paper", "injection_molding_paper", ["openinjmoldsim", "2311-5521/5/2/84"], [ACQUIRED_DIR, ROOT / "data" / "workspace"], ["openinjmoldsim", "fluids-05-02-00084"]),
        github_download_row(),
        harvest_learned_queries_row(),
        robotics_knowledge_row(),
    ]

    rows.sort(key=lambda row: (row["acquired_count"], row["candidate_count"], row["source"].lower()), reverse=True)
    countable_rows = [row for row in rows if not row.get("_exclude_from_totals")]
    for row in rows:
        row.pop("_exclude_from_totals", None)

    # Calculate Gemini decoding wait count from universal_growth.db
    gemini_wait_count = 0
    try:
        if GROWTH_DB.exists():
            con = sqlite3.connect(str(GROWTH_DB))
            con.row_factory = sqlite3.Row
            con.execute("""
                CREATE TABLE IF NOT EXISTS ai_summaries_tracking (
                    external_id TEXT PRIMARY KEY,
                    summarized_at TEXT
                )
            """)
            con.commit()
            processed = set(str(r[0]) for r in con.execute("SELECT external_id FROM ai_summaries_tracking").fetchall() if r[0])
            all_downloaded = con.execute("""
                SELECT id, external_id FROM public_api_acquisitions 
                WHERE status = 'downloaded' AND local_path IS NOT NULL AND local_path != ''
            """).fetchall()
            gemini_wait_count = sum(1 for r in all_downloaded if str(r[0]) not in processed and str(r[1] or '') not in processed)
            con.close()
    except Exception as exc:
        print(f"Failed to calculate Gemini wait count: {exc}")

    return {
        "schema": "clawstack.material_source_inventory.v1",
        "updated_at": now_jst(),
        "total_acquired_count": sum(row["acquired_count"] for row in countable_rows),
        "total_candidate_count": sum(row["candidate_count"] for row in countable_rows),
        "gemini_decoding_wait_count": gemini_wait_count,
        "acquisition_queue": QUEUE_PATH.relative_to(ROOT).as_posix(),
        "rows": rows,
    }


def main():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory()
    OUTPUT_PATH.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] wrote {OUTPUT_PATH}")
    print(f"[OK] acquired={inventory['total_acquired_count']} candidates={inventory['total_candidate_count']}")


if __name__ == "__main__":
    main()
