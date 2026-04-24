#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fetch_ai_public_sources
import fetch_local_llm_oss_digest


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "ai_strategy_scout_local_status.json"
JSON_PATH = WORKSPACE / "ai_strategy_scout_local_digest.json"
MD_PATH = WORKSPACE / "ai_strategy_scout_local_digest.md"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_local_digest() -> dict:
    results: list[dict] = []
    errors: list[dict] = []
    for source in fetch_local_llm_oss_digest.SOURCES:
        try:
            results.append(fetch_local_llm_oss_digest.fetch_source(source))
        except Exception as exc:
            errors.append(
                {
                    "category": source.category,
                    "source": source.source,
                    "url": source.url,
                    "error": str(exc),
                }
            )
    digest = fetch_local_llm_oss_digest.build_digest(source_results=results, days=14, limit=4)
    digest["errors"] = errors
    digest["sources"] = results
    return digest


def fetch_public_digest() -> dict:
    payload = {
        "generatedAt": now_jst_text(),
        "sources": [
            {
                "category": "Official public sources",
                "source": "Rowan Cheung / The Rundown AI",
                "results": fetch_ai_public_sources.extract_homepage_links(
                    "https://rowancheung.com/",
                    link_pattern=r"rowancheung\.com|rundown\.ai|therundown\.ai",
                ),
            },
            {
                "category": "Official public sources",
                "source": "Ethan Mollick / One Useful Thing",
                "results": fetch_ai_public_sources.extract_homepage_links(
                    "https://www.oneusefulthing.org/",
                    link_pattern=r"oneusefulthing\.org",
                ),
            },
            {
                "category": "Official public sources",
                "source": "Allie K. Miller",
                "results": fetch_ai_public_sources.extract_homepage_links(
                    "https://www.alliekmiller.com/",
                    link_pattern=r"alliekmiller\.com/(resources|courses|home|$)|youtube\.com/@AKMofficial",
                ),
            },
            {
                "category": "Official public sources",
                "source": "Logan Kilpatrick / Google Blog",
                "results": fetch_ai_public_sources.extract_rss("https://blog.google/authors/logan-kilpatrick/rss/"),
            },
            {
                "category": "Creative Trends",
                "source": "Runway / Video Generation",
                "results": fetch_ai_public_sources.extract_homepage_links("https://runwayml.com/blog", link_pattern=r"blog/.*"),
            },
            {
                "category": "Creative Trends",
                "source": "Suno / Music Generation",
                "results": fetch_ai_public_sources.extract_homepage_links("https://suno.com/blog", link_pattern=r"blog/.*"),
            },
            {
                "category": "Creative Trends",
                "source": "ComfyUI / Anime Workflows",
                "results": fetch_ai_public_sources.extract_homepage_links("https://blog.comfy.org/", link_pattern=r"blog/.*"),
            },
            {
                "category": "Manufacturing & Fab",
                "source": "Cults3D / 3D Trends Blog",
                "results": fetch_ai_public_sources.extract_rss("https://cults3d.com/en/blog.rss"),
            },
            {
                "category": "Manufacturing & Fab",
                "source": "3DPrint.com / Industry News",
                "results": fetch_ai_public_sources.extract_rss("https://3dprint.com/feed"),
            },
            {
                "category": "Manufacturing & Fab",
                "source": "Creality Official / Ender GitHub",
                "results": fetch_ai_public_sources.extract_rss("https://github.com/CrealityOfficial/Ender-3_V3_KE_Klipper/releases.atom"),
            },
        ],
    }
    # Defensive robustness: Filter out individual source failures
    sanitized_sources = []
    for s in payload["sources"]:
        try:
            # results is already populated by extract_rss/extract_homepage_links
            sanitized_sources.append(s)
        except Exception:
            s["results"] = []
            sanitized_sources.append(s)
    payload["sources"] = sanitized_sources
    return payload


# --- Hub Registry for Architectural Sentinel ---
HUB_REGISTRY = {
    "Creative Studio": {
        "path": "apps/creative_studio/index.html",
        "keywords": ["video", "anime", "manga", "cinema", "comfyui", "kling", "luma", "runway", "gen-3", "gen-4", "cogvideo"]
    },
    "Audio Lab": {
        "path": "apps/audio_lab/index.html",
        "keywords": ["audio", "music", "suno", "udio", "rvc", "voice", "speech", "stable audio"]
    },
    "Knowledge Hub": {
        "path": "apps/knowledge_hub/index.html",
        "keywords": ["note", "knowledge", "obsidian", "mcp", "rag", "summary", "semantic", "notebooklm"]
    },
    "Pub-Hub": {
        "path": "apps/pub_hub/index.html",
        "keywords": ["kindle", "ebook", "kdp", "epub", "formatting", "writing", "author", "kimi"]
    },
    "3D Fab-Forge": {
        "path": "apps/3d_fab_forge/index.html",
        "keywords": ["3d print", "ender", "creality", "klipper", "stl", "printables", "cults3d", "slicing", "cad", "monetization", "etsy"]
    },
    "Ops Toolbox": {
        "path": "apps/operations_toolbox/index.html",
        "keywords": ["clean", "disk", "maintenance", "system", "monitoring", "docker"]
    }
}

def analyze_adoption(combined: dict) -> list[dict]:
    """Analyzes daily items and recommends architectural adoption decisions."""
    recommendations = []
    seen_recommendations = set()
    
    # Collect all items
    all_items = []
    for item in combined["localDigest"]["categories"].values():
        all_items.extend(item)
    for source in combined["publicDigest"]["sources"]:
        all_items.extend(source.get("results", []))
    
    # Keyword Matching
    hub_scores = {name: [] for name in HUB_REGISTRY.keys()}
    potential_new = []

    for item in all_items:
        title = item.get("title", "").lower()
        matched = False
        for hub_name, hub_info in HUB_REGISTRY.items():
            if any(kw in title for kw in hub_info["keywords"]):
                hub_scores[hub_name].append(item)
                matched = True
        
        # Identify high-impact singleton potential (e.g. Robotics, 3D printing)
        if not matched and any(kw in title for kw in ["robot", "cad", "3d print", "automation"]):
           potential_new.append(item)

    # Generate Recommendations
    for hub_name, items in hub_scores.items():
        if items:
            recommendations.append({
                "type": "ADOPT_INTEGRATE",
                "hub": hub_name,
                "reason": f"Matches {len(items)} new developments in this domain.",
                "items": [i["title"] for i in items[:3]]
            })

    if len(potential_new) >= 2:
        recommendations.append({
            "type": "ADOPT_NEW",
            "hub": "Emerging Technologies",
            "reason": "Multiple developments in uncategorized high-impact domains.",
            "items": [i["title"] for i in potential_new[:3]]
        })

    return recommendations

def build_markdown(combined: dict) -> str:
    recommendations = analyze_adoption(combined)
    
    lines = [
        "# AI Strategy Scout: Architectural Sentinel Edition",
        "",
        f"- Generated at: {combined['generatedAt']}",
        f"- Mode: {combined['mode']}",
        "",
    ]
    
    if recommendations:
        lines.extend(["## 🏛️ [DECISION] Architectural Recommendations", ""])
        for rec in recommendations:
            icon = "🔌" if rec["type"] == "ADOPT_INTEGRATE" else "🏠"
            lines.append(f"### {icon} {rec['type']}: {rec['hub']}")
            lines.append(f"- **Rationale**: {rec['reason']}")
            for item in rec["items"]:
                lines.append(f"  - {item}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend(["## Local LLM / OSS", ""])
    for category, rows in combined["localDigest"]["categories"].items():
        lines.append(f"### {category}")
        if not rows:
            lines.append("- No items")
            lines.append("")
            continue
        for row in rows:
            freshness = row.get("freshness", "reference")
            published = row.get("published") or "n/a"
            lines.append(f"- {row.get('title')} [{freshness}]")
            lines.append(f"  Source: {row.get('source')} | Published: {published}")
            lines.append(f"  {row.get('url')}")
        lines.append("")

    lines.extend(["## Official Public Sources", ""])
    for source_entry in combined["publicDigest"]["sources"]:
        lines.append(f"### {source_entry['source']}")
        results = source_entry.get("results", [])
        if not results:
            lines.append("- No items")
            lines.append("")
            continue
        for row in results:
            lines.append(f"- {row.get('title')}")
            lines.append(f"  {row.get('url')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    status = {
        "startedAt": now_jst_text(),
        "stage": "running",
        "mode": "local_no_api_cost",
    }
    write_json(STATUS_PATH, status)

    local_digest = fetch_local_digest()
    public_digest = fetch_public_digest()
    combined = {
        "generatedAt": now_jst_text(),
        "mode": "local_no_api_cost",
        "localDigest": local_digest,
        "publicDigest": public_digest,
    }
    write_json(JSON_PATH, combined)
    MD_PATH.write_text(build_markdown(combined), encoding="utf-8")

    status.update(
        {
            "stage": "completed",
            "finishedAt": now_jst_text(),
            "jsonPath": str(JSON_PATH),
            "markdownPath": str(MD_PATH),
            "localSourcesChecked": local_digest.get("sourcesChecked", 0),
            "publicSourcesChecked": len(public_digest.get("sources", [])),
            "errorSources": local_digest.get("errors", []),
        }
    )
    write_json(STATUS_PATH, status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
