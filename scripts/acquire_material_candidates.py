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
        "pending": REGISTERED_OR_MANUAL_SOURCES,
        "errors": errors,
    }
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] acquired_now={len(acquired)} pending={len(REGISTERED_OR_MANUAL_SOURCES)} errors={len(errors)}")
    print(f"[OK] wrote {QUEUE_PATH}")


if __name__ == "__main__":
    main()
