import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "data" / "workspace" / "apps" / "growth_dashboard"
ACQUIRED_DIR = ROOT / "data" / "web_acquired_materials"
QUEUE_PATH = DASHBOARD_DIR / "material_acquisition_queue.json"
ROBOFLOW_CANDIDATES_PATH = DASHBOARD_DIR / "roboflow_candidate_datasets.json"
QUALITY_SCOUT_PATH = ROOT / "data" / "workspace" / "quality_manufacturing_source_scout_status.json"
JST = timezone(timedelta(hours=9))


DIRECT_FREE_SOURCES = [
    {
        "source": "openInjMoldSim Paper",
        "title": "Verification and Validation of openInjMoldSim, an Open-Source Solver to Model the Filling Stage of Thermoplastic Injection Molding",
        "url": "https://mdpi-res.com/d_attachment/fluids/fluids-05-00084/article_deploy/fluids-05-00084-v2.pdf",
        "landing_url": "https://www.mdpi.com/2311-5521/5/2/84",
        "license_note": "MDPI open-access article. Downloaded from the publisher mdpi-res PDF endpoint.",
        "target_path": ACQUIRED_DIR / "openinjmoldsim" / "fluids-05-02-00084-openInjMoldSim.pdf",
    }
]

REGISTERED_OR_MANUAL_SOURCES = [
    {
        "source": "Scribd",
        "action": "authorized_subscription_download",
        "priority": 1,
        "reason": "Subscription/login source. Use only authorized access and existing paid account; no bypass.",
    },
    {
        "source": "Kaggle datasets",
        "action": "registration_and_license_check",
        "priority": 1,
        "reason": "Kaggle requires account/API token and per-dataset license review before download.",
    },
    {
        "source": "MVTec AD",
        "action": "registration_and_license_check",
        "priority": 1,
        "reason": "Dataset is valuable for visual inspection, but registration/license acceptance is required.",
    },
    {
        "source": "Kolektor Surface-Defect Dataset",
        "action": "registration_and_license_check",
        "priority": 1,
        "reason": "Industrial defect dataset; confirm access terms before mirroring locally.",
    },
    {
        "source": "Roboflow Universe",
        "action": "project_license_selection",
        "priority": 2,
        "reason": "Public dataset platform; each project has its own license and quality level.",
    },
]


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def roboflow_pending_items():
    data = load_json(ROBOFLOW_CANDIDATES_PATH, {})
    items = data.get("items", []) if isinstance(data.get("items"), list) else []
    pending = []
    for item in items:
        pending.append(
            {
                "source": "Roboflow Universe",
                "dataset": item.get("dataset"),
                "category": item.get("category"),
                "url": item.get("url"),
                "action": "user_export_after_license_review",
                "priority": item.get("priority", 2),
                "reason": "Requires logged-in Roboflow access, dataset license check, and export format selection before local download.",
                "recommended_export": ["YOLOv8", "COCO"],
                "images": item.get("images"),
                "downloads": item.get("downloads"),
            }
        )
    return pending


def scout_login_or_review_items(existing_sources):
    data = load_json(QUALITY_SCOUT_PATH, {})
    sources = data.get("sources", []) if isinstance(data.get("sources"), list) else []
    pending = []
    seen = {str(source).lower() for source in existing_sources}
    for item in sources:
        cost_label = str(item.get("cost_label") or "").upper()
        name = str(item.get("name") or "")
        if not name or name.lower() in seen:
            continue
        if cost_label not in {"FREE_REG", "PAID", "CHECK"}:
            continue
        action = "registration_and_license_check"
        if cost_label == "PAID":
            action = "user_purchase_or_subscription_approval"
        elif cost_label == "CHECK":
            action = "source_legality_check"
        pending.append(
            {
                "source": name,
                "url": item.get("url"),
                "action": action,
                "priority": item.get("priority", 3),
                "cost_label": cost_label,
                "domains": item.get("domains", []),
                "reason": item.get("why") or "Review access terms before downloading or reusing material.",
                "next_query": item.get("next_query"),
                "recommended_user_action": "Open the URL, create/login to an account if needed, review license/export terms, then tell K10 which files or dataset export to acquire.",
            }
        )
    pending.sort(key=lambda row: (int(row.get("priority") or 9), row.get("cost_label", ""), row.get("source", "")))
    return pending


def now_jst():
    return datetime.now(JST).replace(microsecond=0).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_source(source):
    target = Path(source["target_path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size == 0:
        req = urllib.request.Request(source["url"], headers={"User-Agent": "ClawstackMaterialScout/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()
        target.write_bytes(content)
    stat = target.stat()
    return {
        "source": source["source"],
        "title": source["title"],
        "status": "acquired",
        "url": source["url"],
        "landing_url": source["landing_url"],
        "path": target.relative_to(ROOT).as_posix(),
        "size_bytes": stat.st_size,
        "sha256": sha256_file(target),
        "acquired_at": now_jst(),
        "license_note": source["license_note"],
    }


def main():
    acquired = []
    errors = []
    for source in DIRECT_FREE_SOURCES:
        try:
            acquired.append(download_source(source))
        except Exception as exc:
            errors.append({"source": source["source"], "status": "error", "error": str(exc)})

    roboflow_items = roboflow_pending_items()
    base_pending = [
        source
        for source in REGISTERED_OR_MANUAL_SOURCES
        if not (roboflow_items and source.get("source") == "Roboflow Universe")
    ]
    pending = base_pending + roboflow_items + scout_login_or_review_items(
        [source.get("source") for source in base_pending] + ["Roboflow Universe"]
    )
    queue = {
        "schema": "clawstack.material_acquisition_queue.v1",
        "updated_at": now_jst(),
        "policy": {
            "direct_free": "download immediately from official/open pages",
            "free_reg": "queue until registration/API token/license acceptance is available",
            "paid": "queue until user explicitly approves paid/subscription use",
            "no_bypass": True,
        },
        "acquired_now": acquired,
        "pending": pending,
        "errors": errors,
    }
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] acquired_now={len(acquired)} pending={len(pending)} errors={len(errors)}")
    print(f"[OK] wrote {QUEUE_PATH}")


if __name__ == "__main__":
    main()
