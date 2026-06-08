import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
SCRIBD_DIR = ROOT / "data" / "scribd_downloads"
OUT_JSON = WORKSPACE / "scribd_related_source_scout_status.json"
OUT_MD = WORKSPACE / "scribd_related_source_scout_status.md"
JST = timezone(timedelta(hours=9))

TOPICS: dict[str, list[str]] = {
    "moldflow_self_solver": [
        "Moldflow Insight training",
        "mold flow analysis injection molding",
        "injection molding simulation fill pack",
        "polymer melt flow simulation",
        "moldflow tutorial gate runner cooling warpage",
    ],
    "cetol_tolerance": [
        "CETOL 6 Sigma tolerance analysis",
        "3D tolerance stack up analysis",
        "dimensional tolerance analysis monte carlo",
        "assembly variation analysis GD&T",
    ],
    "press_progressive_die": [
        "progressive die design press tool",
        "sheet metal stamping springback analysis",
        "blanking bending forming die design",
        "strip layout progressive die",
    ],
    "iatf_audit_training": [
        "IATF 16949 internal audit training",
        "automotive quality audit checklist",
        "process audit manufacturing quality",
        "control plan PFMEA internal audit",
    ],
}

DOMAIN_WEIGHTS = {
    "moldflow_self_solver": 5,
    "cetol_tolerance": 4,
    "press_progressive_die": 4,
    "iatf_audit_training": 3,
}

EXTS = {".pdf", ".docx", ".txt", ".md"}


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def safe_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def topic_terms() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for domain, queries in TOPICS.items():
        terms: set[str] = set()
        for query in queries:
            for token in re.findall(r"[A-Za-z0-9+&.-]{3,}", query.lower()):
                terms.add(token)
        out[domain] = terms
    return out


def classify_title(title: str) -> dict[str, Any]:
    terms_by_domain = topic_terms()
    hay = title.lower()
    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    for domain, terms in terms_by_domain.items():
        hits = sorted(term for term in terms if term in hay)
        score = len(hits) * DOMAIN_WEIGHTS.get(domain, 1)
        if score:
            scores[domain] = score
            matched[domain] = hits[:8]
    best_domain = max(scores.items(), key=lambda kv: kv[1])[0] if scores else "unknown"
    return {
        "domain": best_domain,
        "score": scores.get(best_domain, 0),
        "scores": scores,
        "matched_terms": matched,
    }


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory_downloads(limit_hash_mb: int = 50) -> list[dict[str, Any]]:
    rows = []
    if not SCRIBD_DIR.exists():
        return rows
    for path in sorted(SCRIBD_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        stat = path.stat()
        cls = classify_title(path.name)
        sha1 = None
        if stat.st_size <= limit_hash_mb * 1024 * 1024:
            try:
                sha1 = file_sha1(path)
            except Exception:
                sha1 = None
        rows.append(
            {
                "path": str(path),
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
                "sha1": sha1,
                **cls,
            }
        )
    rows.sort(key=lambda r: (int(r.get("score") or 0), r.get("modified_at") or ""), reverse=True)
    return rows


def scribd_search_url(query: str) -> str:
    return "https://www.scribd.com/search?content_type=documents&query=" + urllib.parse.quote(query)


def fetch_public_scribd_candidates(query: str, max_results: int) -> list[dict[str, Any]]:
    url = scribd_search_url(query)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 ClawstackScribdScout/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read(1024 * 1024).decode("utf-8", errors="replace")
    except Exception as exc:
        return [{"query": query, "search_url": url, "error": str(exc)[:300]}]

    seen = set()
    rows = []
    for match in re.finditer(r'href="([^"]*/document/[^"]+)"', text):
        href = html.unescape(match.group(1))
        if href.startswith("/"):
            href = "https://www.scribd.com" + href
        href = href.split("?", 1)[0]
        if href in seen:
            continue
        seen.add(href)
        slug = href.rstrip("/").split("/")[-1].replace("-", " ")
        title = safe_text(slug)
        rows.append(
            {
                "query": query,
                "title": title,
                "url": href,
                "search_url": url,
                **classify_title(title),
            }
        )
        if len(rows) >= max_results:
            break
    return rows


def build_candidates(fetch_public_search: bool, max_results_per_query: int) -> list[dict[str, Any]]:
    rows = []
    for domain, queries in TOPICS.items():
        for query in queries:
            base = {
                "domain_hint": domain,
                "query": query,
                "search_url": scribd_search_url(query),
                "source": "scribd_search_url",
            }
            if fetch_public_search:
                fetched = fetch_public_scribd_candidates(query, max_results_per_query)
                if fetched:
                    rows.extend(fetched)
                    time.sleep(1.0)
                else:
                    rows.append(base)
            else:
                rows.append(base)
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Scribd Related Source Scout",
        "",
        f"- Updated: {payload['updated_at']}",
        f"- Mode: {payload['mode']}",
        f"- Download inventory count: {len(payload['download_inventory'])}",
        f"- Candidate count: {len(payload['candidates'])}",
        "",
        "## Safety Policy",
        "",
        "- Do not bypass paywalls, DRM, authentication, or platform controls.",
        "- Store metadata, links, and user-authorized downloads only.",
        "- Use extracted text for internal learning only when access is legitimate.",
        "- Keep automatic code modification disabled from the Scribd pipeline.",
        "",
        "## Priority Topics",
        "",
    ]
    for domain, queries in TOPICS.items():
        lines.append(f"### {domain}")
        for query in queries:
            lines.append(f"- [{query}]({scribd_search_url(query)})")
        lines.append("")

    lines.extend(["## Existing Download Inventory", ""])
    for row in payload["download_inventory"][:30]:
        lines.append(
            f"- score={row.get('score', 0)} domain={row.get('domain')} "
            f"size={row.get('size_bytes')} name={row.get('name')}"
        )
    lines.append("")
    lines.extend(["## Candidate Links", ""])
    for row in payload["candidates"][:50]:
        title = row.get("title") or row.get("query")
        url = row.get("url") or row.get("search_url")
        lines.append(f"- domain={row.get('domain') or row.get('domain_hint')} [{title}]({url})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Copyright-safe Scribd source scout and inventory.")
    parser.add_argument("--fetch-public-search", action="store_true", help="Fetch public Scribd search pages, no login/download.")
    parser.add_argument("--max-results-per-query", type=int, default=5)
    args = parser.parse_args()

    payload = {
        "schema": "clawstack.scribd_related_source_scout.v1",
        "updated_at": now_iso(),
        "mode": "public_search" if args.fetch_public_search else "search_url_inventory",
        "safety_policy": {
            "no_bypass": True,
            "no_unauthorized_download": True,
            "metadata_first": True,
            "autonomous_code_change": False,
        },
        "topics": TOPICS,
        "download_inventory": inventory_downloads(),
        "candidates": build_candidates(args.fetch_public_search, max(1, min(args.max_results_per_query, 10))),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(f"[OK] wrote {OUT_JSON}")
    print(f"[OK] wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
