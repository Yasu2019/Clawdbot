import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV = ROOT / ".env"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "asset_manifest.json"
DEFAULT_DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"
USER_AGENT = "AtsugiMechaCityAssetSearch/1.0 (license-aware local workflow)"

DENY_LICENSE_MARKERS = (
    "noncommercial",
    "no derivatives",
    "nonderivative",
    "no-derivatives",
    "fair use",
    "all rights reserved",
    "unknown",
)

ALLOW_LICENSE_MARKERS = (
    "cc0",
    "public domain",
    "cc by",
    "cc-by",
    "creative commons attribution",
    "pexels license",
    "unsplash license",
)


def read_env(path):
    env = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def env_first(env, *keys):
    for key in keys:
        value = env.get(key)
        if value:
            return value
    return None


def request_json(url, headers=None, timeout=30):
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url, output_path, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        output_path.write_bytes(response.read())


def strip_html(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(text))).strip()


def metadata_value(extmetadata, key):
    item = extmetadata.get(key) or {}
    return strip_html(item.get("value", ""))


def is_license_allowed(name, url=""):
    text = f"{name} {url}".lower()
    if not text.strip():
        return False
    if any(marker in text for marker in DENY_LICENSE_MARKERS):
        return False
    return any(marker in text for marker in ALLOW_LICENSE_MARKERS)


def normalize_item(
    source,
    asset_id,
    title,
    page_url,
    image_url,
    thumbnail_url,
    author,
    license_name,
    license_url,
    width=None,
    height=None,
    usage="reference_or_texture_candidate",
):
    if license_url.startswith("//"):
        license_url = f"https:{license_url}"
    if page_url.startswith("//"):
        page_url = f"https:{page_url}"
    return {
        "source": source,
        "asset_id": str(asset_id),
        "title": title or "",
        "page_url": page_url or "",
        "image_url": image_url or "",
        "thumbnail_url": thumbnail_url or "",
        "author": strip_html(author),
        "license_name": strip_html(license_name),
        "license_url": license_url or "",
        "license_allowed_by_filter": is_license_allowed(license_name, license_url),
        "usage": usage,
        "width": width,
        "height": height,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def search_wikimedia(query, limit):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": "900",
        "origin": "*",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = request_json(url)
    pages = data.get("query", {}).get("pages", {})
    items = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        meta = info.get("extmetadata") or {}
        license_name = metadata_value(meta, "LicenseShortName") or metadata_value(meta, "UsageTerms")
        license_url = metadata_value(meta, "LicenseUrl")
        item = normalize_item(
            source="wikimedia",
            asset_id=page.get("pageid", page.get("title", "")),
            title=metadata_value(meta, "ObjectName") or page.get("title", ""),
            page_url=info.get("descriptionurl", ""),
            image_url=info.get("url", ""),
            thumbnail_url=info.get("thumburl", ""),
            author=metadata_value(meta, "Artist") or metadata_value(meta, "Credit"),
            license_name=license_name,
            license_url=license_url,
            width=info.get("width"),
            height=info.get("height"),
        )
        if item["license_allowed_by_filter"]:
            items.append(item)
    return items


def search_pexels(query, limit, api_key):
    if not api_key:
        return []
    params = {
        "query": query,
        "per_page": str(limit),
        "orientation": "landscape",
    }
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(params)
    data = request_json(url, headers={"Authorization": api_key})
    items = []
    for photo in data.get("photos", []):
        src = photo.get("src") or {}
        item = normalize_item(
            source="pexels",
            asset_id=photo.get("id", ""),
            title=photo.get("alt", "") or f"Pexels photo {photo.get('id', '')}",
            page_url=photo.get("url", ""),
            image_url=src.get("large2x") or src.get("large") or src.get("original", ""),
            thumbnail_url=src.get("medium", ""),
            author=photo.get("photographer", ""),
            license_name="Pexels License",
            license_url="https://www.pexels.com/license/",
            width=photo.get("width"),
            height=photo.get("height"),
        )
        if item["license_allowed_by_filter"]:
            items.append(item)
    return items


def search_unsplash(query, limit, access_key):
    if not access_key:
        return []
    params = {
        "query": query,
        "per_page": str(limit),
        "orientation": "landscape",
    }
    url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(params)
    data = request_json(
        url,
        headers={
            "Authorization": f"Client-ID {access_key}",
            "Accept-Version": "v1",
        },
    )
    items = []
    for photo in data.get("results", []):
        urls = photo.get("urls") or {}
        user = photo.get("user") or {}
        item = normalize_item(
            source="unsplash",
            asset_id=photo.get("id", ""),
            title=photo.get("alt_description") or photo.get("description") or f"Unsplash photo {photo.get('id', '')}",
            page_url=(photo.get("links") or {}).get("html", ""),
            image_url=urls.get("regular") or urls.get("full") or urls.get("raw", ""),
            thumbnail_url=urls.get("thumb", ""),
            author=user.get("name", ""),
            license_name="Unsplash License",
            license_url="https://unsplash.com/license",
            width=photo.get("width"),
            height=photo.get("height"),
        )
        if item["license_allowed_by_filter"]:
            items.append(item)
    return items


def safe_filename(item):
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{item['source']}_{item['asset_id']}").strip("_")
    return (slug or f"asset_{int(time.time())}")[:120] + ".jpg"


def maybe_download(items, download_dir, max_downloads):
    download_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for item in items[:max_downloads]:
        url = item.get("image_url")
        if not url:
            continue
        output = download_dir / safe_filename(item)
        try:
            download_file(url, output)
            item["local_path"] = str(output)
            downloaded.append(str(output))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            item["download_error"] = str(exc)
    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Search license-aware city reference photos.")
    parser.add_argument("--query", required=True, help="Search query, e.g. 'Hon-Atsugi station'.")
    parser.add_argument("--sources", default="wikimedia", help="Comma-separated sources: wikimedia,pexels,unsplash.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum candidates per source, capped at 20.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV), help=".env file path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output manifest JSON.")
    parser.add_argument("--download", action="store_true", help="Download candidate images after manifest search.")
    parser.add_argument("--download-dir", default=str(DEFAULT_DOWNLOAD_DIR), help="Download directory.")
    parser.add_argument("--max-downloads", type=int, default=2, help="Maximum downloads, capped at 5.")
    args = parser.parse_args()

    env = read_env(Path(args.env_file))
    sources = [source.strip().lower() for source in args.sources.split(",") if source.strip()]
    limit = max(1, min(args.limit, 20))
    pexels_key = env_first(env, "PEXELS_API_KEY")
    unsplash_key = env_first(env, "UNSPLASH_ACCESS_KEY", "Unsplash_Access Key")

    results = []
    errors = []

    for source in sources:
        try:
            if source == "wikimedia":
                results.extend(search_wikimedia(args.query, limit))
            elif source == "pexels":
                if not pexels_key:
                    errors.append({"source": source, "error": "PEXELS_API_KEY is missing."})
                else:
                    results.extend(search_pexels(args.query, limit, pexels_key))
            elif source == "unsplash":
                if not unsplash_key:
                    errors.append({"source": source, "error": "UNSPLASH_ACCESS_KEY or Unsplash_Access Key is missing."})
                else:
                    results.extend(search_unsplash(args.query, limit, unsplash_key))
            else:
                errors.append({"source": source, "error": "Unknown source."})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append({"source": source, "error": str(exc)})

    if args.download and results:
        maybe_download(results, Path(args.download_dir), max(1, min(args.max_downloads, 5)))

    manifest = {
        "query": args.query,
        "sources": sources,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "google_maps_or_street_view": "forbidden",
            "license_filter": "exclude NC, ND, fair-use, unknown, and all-rights-reserved assets",
            "usage_requires_attribution_review": True,
        },
        "count": len(results),
        "errors": errors,
        "assets": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "count": len(results), "errors": errors}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
