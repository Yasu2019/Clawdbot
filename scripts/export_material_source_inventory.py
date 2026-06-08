import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "data" / "workspace" / "apps" / "growth_dashboard"
OUTPUT_PATH = DASHBOARD_DIR / "material_source_inventory.json"
ACQUIRED_DIR = ROOT / "data" / "web_acquired_materials"
QUEUE_PATH = DASHBOARD_DIR / "material_acquisition_queue.json"

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


def build_inventory():
    dataset_paths = [
        ROOT / "data" / "datasets",
        ROOT / "data" / "kaggle",
        ROOT / "data" / "workspace" / "datasets",
    ]
    github_items = file_inventory([ROOT / "data" / "github_downloads"])

    rows = [
        scribd_row(),
        youtube_row(),
        scout_backed_row("Kaggle datasets", "dataset_platform", ["kaggle"], dataset_paths, ["kaggle"]),
        scout_backed_row("MVTec AD", "visual_inspection_dataset", ["mvtec"], dataset_paths, ["mvtec"]),
        scout_backed_row("Kolektor Surface-Defect Dataset", "visual_inspection_dataset", ["kolektor"], dataset_paths, ["kolektor"]),
        scout_backed_row("Roboflow Universe", "vision_dataset_platform", ["roboflow"], dataset_paths, ["roboflow"]),
        scout_backed_row("openInjMoldSim Paper", "injection_molding_paper", ["openinjmoldsim", "2311-5521/5/2/84"], [ACQUIRED_DIR, ROOT / "data" / "workspace"], ["openinjmoldsim", "fluids-05-02-00084"]),
        {
            "source": "GitHub",
            "category": "code_and_reference",
            "acquired_count": len(github_items),
            "candidate_count": 0,
            "status": "acquired" if github_items else "not_acquired",
            "latest_at": github_items[0]["modified_at"] if github_items else "",
            "evidence": "data/github_downloads",
            "note": "Local files fetched from GitHub-related collection folders.",
            "examples": [item["name"] for item in github_items[:5]],
        },
    ]

    rows.sort(key=lambda row: (row["acquired_count"], row["candidate_count"], row["source"].lower()), reverse=True)
    return {
        "schema": "clawstack.material_source_inventory.v1",
        "updated_at": now_jst(),
        "total_acquired_count": sum(row["acquired_count"] for row in rows),
        "total_candidate_count": sum(row["candidate_count"] for row in rows),
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
