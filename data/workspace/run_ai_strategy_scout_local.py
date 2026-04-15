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
        ],
    }
    return payload


def build_markdown(combined: dict) -> str:
    lines = [
        "# AI Strategy Scout (Local / No API Cost)",
        "",
        f"- Generated at: {combined['generatedAt']}",
        f"- Mode: {combined['mode']}",
        "",
        "## Local LLM / OSS",
        "",
    ]
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
