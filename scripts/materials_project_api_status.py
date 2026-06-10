import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_JSON = WORKSPACE / "materials_project_api_status.json"
STATUS_MD = WORKSPACE / "materials_project_api_status.md"
ENV_PATH = ROOT / ".env"
JST = timezone(timedelta(hours=9))

KEY_NAMES = [
    "MP_API_KEY",
    "Materials_Project",
    "MATERIALS_PROJECT_API_KEY",
    "MAPI_KEY",
]


def now_jst():
    return datetime.now(JST).replace(microsecond=0).isoformat()


def load_env_file():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_api_key():
    load_env_file()
    for name in KEY_NAMES:
        value = os.environ.get(name)
        if value:
            return name, value
    return "", ""


def api_query(api_key):
    params = urllib.parse.urlencode(
        {
            "material_ids": "mp-149",
            "_fields": "material_id,formula_pretty,band_gap,is_stable,energy_above_hull",
        }
    )
    url = "https://api.materialsproject.org/materials/summary/?" + params
    request = urllib.request.Request(
        url,
        headers={
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "User-Agent": "ClawstackMaterialsProjectProbe/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data") if isinstance(payload, dict) else []
    return data if isinstance(data, list) else []


def build_status():
    key_name, api_key = get_api_key()
    status = {
        "schema": "clawstack.materials_project_api_status.v1",
        "updated_at": now_jst(),
        "source": "Materials Project",
        "api_base": "https://api.materialsproject.org",
        "docs": "https://docs.materialsproject.org/downloading-data/using-the-api/getting-started",
        "key_present": bool(api_key),
        "key_name": key_name,
        "key_value_stored": False,
        "api_ok": False,
        "sample_count": 0,
        "sample_materials": [],
        "recommended_use": [
            "materials property lookup for CAE grounding",
            "screening candidate material systems",
            "education and validation examples for material-data pipelines",
        ],
        "limits": [
            "Do not store or print API key values.",
            "Review Materials Project terms before bulk download or redistribution.",
            "Use small, targeted queries first; do not mirror the database.",
        ],
    }
    if not api_key:
        status["status"] = "missing_api_key"
        status["next_action"] = "Set MP_API_KEY or Materials_Project in .env."
        return status
    try:
        rows = api_query(api_key)
        status["api_ok"] = True
        status["status"] = "api_ready"
        status["sample_count"] = len(rows)
        status["sample_materials"] = [
            {
                "material_id": row.get("material_id"),
                "formula_pretty": row.get("formula_pretty"),
                "band_gap": row.get("band_gap"),
                "is_stable": row.get("is_stable"),
                "energy_above_hull": row.get("energy_above_hull"),
            }
            for row in rows[:3]
            if isinstance(row, dict)
        ]
        status["next_action"] = "Use targeted materials queries after selecting a CAE/material question."
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        status["status"] = "api_http_error"
        status["http_status"] = exc.code
        status["error"] = body
        status["next_action"] = "Check API key validity and query parameters."
    except Exception as exc:
        status["status"] = "api_error"
        status["error"] = str(exc)[:300]
        status["next_action"] = "Check network access and Materials Project API availability."
    return status


def render_markdown(status):
    lines = [
        "# Materials Project API Status",
        "",
        f"- Updated: {status.get('updated_at')}",
        f"- Status: {status.get('status')}",
        f"- API key present: {status.get('key_present')}",
        f"- Key name: {status.get('key_name') or 'not configured'}",
        f"- API OK: {status.get('api_ok')}",
        f"- Sample count: {status.get('sample_count')}",
        "",
        "## Sample Materials",
        "",
    ]
    for row in status.get("sample_materials", []):
        lines.append(
            f"- {row.get('material_id')} {row.get('formula_pretty')} "
            f"band_gap={row.get('band_gap')} stable={row.get('is_stable')}"
        )
    if not status.get("sample_materials"):
        lines.append("- None")
    lines.extend(["", "## Limits", ""])
    for item in status.get("limits", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Next Action", "", f"- {status.get('next_action')}"])
    return "\n".join(lines) + "\n"


def main():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    status = build_status()
    STATUS_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATUS_MD.write_text(render_markdown(status), encoding="utf-8")
    print(f"[OK] wrote {STATUS_JSON}")
    print(f"[OK] status={status.get('status')} api_ok={status.get('api_ok')} key_present={status.get('key_present')}")
    return 0 if status.get("key_present") else 2


if __name__ == "__main__":
    raise SystemExit(main())
