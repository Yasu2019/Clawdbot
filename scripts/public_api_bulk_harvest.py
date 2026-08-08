# -*- coding: utf-8 -*-
"""Harvest useful metadata/files from configured public APIs into local store + DB."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
DOWNLOAD_ROOT = ROOT / "data" / "public_api_downloads"
MANIFEST_JSONL = WORKSPACE / "public_api_acquisitions.jsonl"
STATUS_PATH = WORKSPACE / "public_api_harvest_status.json"
GROWTH_DB = WORKSPACE / "universal_growth.db"
JST = timezone(timedelta(hours=9))

# North Star / manufacturing relevance
SEARCH_QUERIES = [
    "injection molding simulation",
    "OpenRadioss",
    "progressive die",
    "press forming FEA",
    "surface defect detection",
    "moldflow",
    "blanking simulation",
    "resin fill cavity",
    "interFoam mold filling",
    "sheet metal forming finite element",
    "stamping die design",
    "automated optical inspection manufacturing",
    "progressive strip layout",
    "openfoam injection molding",
    "IATF 16949 quality",
    "tolerance stack analysis",
    "deep drawing simulation",
    "metal stamping defect",
    "プレス成形 有限要素法",
    "めっき技術 密着性",
    "金型設計 順送",
    "公差累積解析 3D",
    "脱脂処理 表面改質",
    "プラスチック成形 金型温度",
]

MAX_FILE_MB = 100
MAX_PER_SOURCE = 12
_ACTIVE_DOMAIN_TAGS: list[str] = []


def set_active_domain_tags(tags: list[str]) -> None:
    global _ACTIVE_DOMAIN_TAGS
    _ACTIVE_DOMAIN_TAGS = list(tags)


def merge_domain_tags(row_tags: list[str] | None) -> list[str]:
    merged = list(_ACTIVE_DOMAIN_TAGS)
    for tag in row_tags or []:
        if tag not in merged:
            merged.append(tag)
    return merged


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def now_jst() -> str:
    return datetime.now(JST).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_db() -> sqlite3.Connection:
    GROWTH_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(GROWTH_DB, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        con.execute("PRAGMA journal_mode=DELETE")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS public_api_acquisitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acquired_at TEXT NOT NULL,
            source TEXT NOT NULL,
            external_id TEXT,
            title TEXT,
            url TEXT,
            local_path TEXT,
            size_bytes INTEGER,
            sha256 TEXT,
            license_note TEXT,
            metadata_json TEXT,
            status TEXT NOT NULL,
            domain_tags TEXT
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_public_api_acq_source ON public_api_acquisitions(source)"
    )
    # record_acquisition の既存行探索用。UNIQUE にはしない — 既存の重複
    # (2026-08-08時点で98,107行中の約97%) を消すまで UNIQUE は張れないため。
    # 重複解消後に scripts/dedupe_acquisitions.py が UNIQUE へ昇格させる。
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_public_api_acq_srcext "
        "ON public_api_acquisitions(source, external_id)"
    )
    con.commit()
    return con


def _license_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)[:500]
    return str(value)[:500]


def record_acquisition(con: sqlite3.Connection, row: dict) -> None:
    # 2026-08-08: (source, external_id) の一意制約が無く無条件INSERTだったため、
    # 収集を回すたびに同一資料が新IDで増殖していた(実測: 一意971件が98,107行)。
    # 既存行があれば更新に切り替える。UNIQUEインデックス作成前でも動くよう、
    # 事前SELECTで既存を探す方式にしている(重複が残っている間も安全)。
    source = row.get("source") or "unknown"
    ext_id = row.get("external_id")
    if ext_id:
        hit = con.execute(
            "SELECT id FROM public_api_acquisitions WHERE source=? AND external_id=? "
            "ORDER BY id LIMIT 1", (source, ext_id)).fetchone()
        if hit:
            con.execute(
                """
                UPDATE public_api_acquisitions
                   SET title=COALESCE(?, title),
                       url=COALESCE(?, url),
                       local_path=COALESCE(?, local_path),
                       size_bytes=COALESCE(?, size_bytes),
                       sha256=COALESCE(?, sha256),
                       metadata_json=?,
                       status=?,
                       domain_tags=?
                 WHERE id=?
                """,
                (row.get("title"), row.get("url"), row.get("local_path"),
                 row.get("size_bytes"), row.get("sha256"),
                 json.dumps(row.get("metadata") or {}, ensure_ascii=False),
                 row.get("status") or "metadata_only",
                 ",".join(merge_domain_tags(row.get("domain_tags"))),
                 hit[0]))
            return
    con.execute(
        """
        INSERT INTO public_api_acquisitions
        (acquired_at, source, external_id, title, url, local_path, size_bytes, sha256,
         license_note, metadata_json, status, domain_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("acquired_at") or now_jst(),
            row.get("source") or "unknown",
            row.get("external_id"),
            row.get("title"),
            row.get("url"),
            row.get("local_path"),
            row.get("size_bytes"),
            row.get("sha256"),
            row.get("license_note"),
            json.dumps(row.get("metadata") or {}, ensure_ascii=False),
            row.get("status") or "metadata_only",
            ",".join(merge_domain_tags(row.get("domain_tags"))),
        ),
    )
    con.commit()
    MANIFEST_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def http_get_json(url: str, headers: dict | None = None, timeout: int = 30) -> dict | list:
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "ClawstackPublicApiHarvest/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def download_url(url: str, dest: Path, headers: dict | None = None) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # 保存名は sha1(external_id:url) で決定的なので、既に取得済みなら再取得しない。
    # 2026-08-08 実測: 存在チェックが無いため同一PDFを最大353回ダウンロードしていた
    # (ディスクは上書きで増えないが帯域と時間を浪費していた)。
    if dest.exists() and dest.stat().st_size > 0:
        if dest.suffix.lower() != ".pdf":
            return True
        try:
            with dest.open("rb") as fh:
                if fh.read(4) == b"%PDF":
                    return True
        except OSError:
            pass
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "ClawstackPublicApiHarvest/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        if len(data) > MAX_FILE_MB * 1024 * 1024:
            return False
        if dest.suffix.lower() == ".pdf" and not data.startswith(b"%PDF"):
            return False
        dest.write_bytes(data)
        return dest.stat().st_size > 0
    except Exception:
        return False


def harvest_openalex(con: sqlite3.Connection, query: str) -> int:
    mailto = os.getenv("OPENALEX_MAILTO") or os.getenv("Materials_Project_ID") or "y.suzuki.hk@gmail.com"
    params = urllib.parse.urlencode(
        {"search": query, "per_page": 5, "mailto": mailto}
    )
    data = http_get_json(f"https://api.openalex.org/works?{params}")
    count = 0
    for item in (data.get("results") or [])[:5]:
        title = item.get("display_name") or item.get("title") or "untitled"
        ext_id = item.get("id") or ""
        url = item.get("id") or item.get("doi") or ""
        row = {
            "acquired_at": now_jst(),
            "source": "openalex",
            "external_id": ext_id,
            "title": title,
            "url": url,
            "local_path": None,
            "status": "metadata_only",
            "license_note": "OpenAlex metadata; follow DOI/publisher for full text",
            "metadata": {
                "query": query,
                "publication_year": item.get("publication_year"),
                "cited_by_count": item.get("cited_by_count"),
                "open_access": item.get("open_access"),
            },
            "domain_tags": ["research", "cae"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def _normalize_doi(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if "doi.org/" in text:
        text = text.split("doi.org/", 1)[1]
    return text.strip().lower()


def harvest_datacite(con: sqlite3.Connection, query: str) -> int:
    params = urllib.parse.urlencode({"query": query, "page[size]": 5})
    data = http_get_json(f"https://api.datacite.org/dois?{params}")
    count = 0
    for item in (data.get("data") or [])[:5]:
        attrs = item.get("attributes") or {}
        titles = attrs.get("titles") or []
        title = (titles[0].get("title") if titles else None) or "untitled"
        doi = _normalize_doi(item.get("id") or attrs.get("doi") or "")
        url = attrs.get("url") or (f"https://doi.org/{doi}" if doi else "")
        row = {
            "acquired_at": now_jst(),
            "source": "datacite",
            "external_id": doi or item.get("id"),
            "title": title,
            "url": url,
            "local_path": None,
            "status": "metadata_only",
            "license_note": "DataCite metadata; check repository license",
            "metadata": {
                "query": query,
                "publisher": attrs.get("publisher"),
                "resource_type": attrs.get("resourceTypeGeneral"),
                "subjects": attrs.get("subjects"),
            },
            "domain_tags": ["dataset", "research"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_europe_pmc(con: sqlite3.Connection, query: str) -> int:
    params = urllib.parse.urlencode(
        {"query": query, "pageSize": 5, "format": "json", "resultType": "core"}
    )
    data = http_get_json(
        f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}"
    )
    count = 0
    for item in (data.get("resultList", {}).get("result") or [])[:5]:
        title = item.get("title") or "untitled"
        ext_id = item.get("id") or item.get("pmid") or item.get("pmcid") or ""
        source = item.get("source") or "EPMC"
        page_url = f"https://europepmc.org/article/{source}/{ext_id}"
        pdf_url = ""
        for entry in item.get("fullTextUrlList", {}).get("fullTextUrl") or []:
            if (entry.get("documentStyle") or "").lower() == "pdf":
                pdf_url = entry.get("url") or ""
                break
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        if pdf_url and (item.get("isOpenAccess") == "Y" or "pmc" in pdf_url.lower()):
            safe = hashlib.sha1(f"{ext_id}:{pdf_url}".encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "europe_pmc" / f"{safe}.pdf"
            if download_url(pdf_url, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
        row = {
            "acquired_at": now_jst(),
            "source": "europe_pmc",
            "external_id": str(ext_id),
            "title": title,
            "url": page_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "Europe PMC OA where available; check record license",
            "metadata": {
                "query": query,
                "pmcid": item.get("pmcid"),
                "doi": item.get("doi"),
                "is_open_access": item.get("isOpenAccess"),
                "pdf_url": pdf_url,
            },
            "domain_tags": ["research", "quality"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_semantic_scholar(con: sqlite3.Connection, query: str) -> int:
    api_key = (os.getenv("SEMANTIC_SCHOLAR_API_KEY") or "").strip()
    fields = "title,url,year,citationCount,externalIds,openAccessPdf,isOpenAccess"
    params = urllib.parse.urlencode({"query": query, "limit": 5, "fields": fields})
    headers = {"User-Agent": "ClawstackPublicApiHarvest/1.0"}
    if api_key:
        headers["x-api-key"] = api_key
        time.sleep(1)
    else:
        time.sleep(5)
    try:
        data = http_get_json(
            f"https://api.semanticscholar.org/graph/v1/paper/search?{params}",
            headers=headers,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return 0
        raise
    count = 0
    for item in (data.get("data") or [])[:5]:
        title = item.get("title") or "untitled"
        ext_ids = item.get("externalIds") or {}
        doi = _normalize_doi(ext_ids.get("DOI") or "")
        paper_id = item.get("paperId") or ""
        page_url = item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
        oa_pdf = (item.get("openAccessPdf") or {}).get("url") or ""
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        if oa_pdf:
            safe = hashlib.sha1(oa_pdf.encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "semantic_scholar" / f"{safe}.pdf"
            if download_url(oa_pdf, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
        row = {
            "acquired_at": now_jst(),
            "source": "semantic_scholar",
            "external_id": doi or paper_id,
            "title": title,
            "url": page_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "Semantic Scholar metadata/OA PDF when available",
            "metadata": {
                "query": query,
                "year": item.get("year"),
                "citation_count": item.get("citationCount"),
                "doi": doi,
                "is_open_access": item.get("isOpenAccess"),
            },
            "domain_tags": ["research", "cae"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_doaj(con: sqlite3.Connection, query: str) -> int:
    path_q = urllib.parse.quote(query)
    data = http_get_json(f"https://doaj.org/api/search/articles/{path_q}?pageSize=5")
    count = 0
    for item in (data.get("results") or [])[:5]:
        bib = item.get("bibjson") or {}
        title = bib.get("title") or "untitled"
        journal = (bib.get("journal") or {}).get("title") or ""
        ext_id = item.get("id") or ""
        links = bib.get("link") or []
        page_url = ""
        for link in links:
            if (link.get("type") or "").lower() == "fulltext":
                page_url = link.get("url") or page_url
        if not page_url and links:
            page_url = links[0].get("url") or ""
        row = {
            "acquired_at": now_jst(),
            "source": "doaj",
            "external_id": str(ext_id),
            "title": title,
            "url": page_url or f"https://doaj.org/article/{ext_id}",
            "local_path": None,
            "status": "metadata_only",
            "license_note": "DOAJ OA article metadata",
            "metadata": {"query": query, "journal": journal, "year": bib.get("year")},
            "domain_tags": ["research", "quality"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_huggingface_datasets(con: sqlite3.Connection, query: str) -> int:
    token = (os.getenv("HF_TOKEN") or os.getenv("Hugging_Face_API_TOKEN") or "").strip()
    params = urllib.parse.urlencode({"search": query, "limit": 5})
    headers = {"User-Agent": "ClawstackPublicApiHarvest/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = http_get_json(f"https://huggingface.co/api/datasets?{params}", headers=headers)
    count = 0
    items = data if isinstance(data, list) else (data.get("datasets") or [])
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        ds_id = item.get("id") or ""
        title = item.get("id") or "untitled"
        page_url = f"https://huggingface.co/datasets/{ds_id}" if ds_id else ""
        row = {
            "acquired_at": now_jst(),
            "source": "huggingface_datasets",
            "external_id": ds_id,
            "title": title,
            "url": page_url,
            "local_path": None,
            "status": "metadata_only",
            "license_note": "Review Hugging Face dataset card license before download",
            "metadata": {
                "query": query,
                "downloads": item.get("downloads"),
                "likes": item.get("likes"),
                "tags": item.get("tags"),
            },
            "domain_tags": ["dataset", "ml"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_ambientcg(con: sqlite3.Connection, query: str) -> int:
    params = urllib.parse.urlencode(
        {"type": "Material", "search": query, "limit": 3, "include": "downloadData"}
    )
    data = http_get_json(f"https://ambientcg.com/api/v2/full_json?{params}")
    count = 0
    for item in (data.get("foundAssets") or [])[:3]:
        asset_id = item.get("assetId") or "asset"
        title = f"AmbientCG {asset_id}"
        folders = item.get("downloadFolders") or {}
        default = folders.get("default") or {}
        paths = default.get("downloadFilepathTypes") or {}
        zip_path = paths.get("zip") or paths.get("gltf") or ""
        page_url = f"https://ambientcg.com/view?id={asset_id}"
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        if zip_path:
            dl_url = "https://ambientcg.com/get?file=" + urllib.parse.quote(zip_path.lstrip("/"))
            safe = hashlib.sha1(asset_id.encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "ambientcg" / f"{safe}.zip"
            if dest.exists() and dest.stat().st_size > 0:
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded_existing"
            elif download_url(dl_url, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
        row = {
            "acquired_at": now_jst(),
            "source": "ambientcg",
            "external_id": asset_id,
            "title": title,
            "url": page_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "CC0 on AmbientCG; verify asset page",
            "metadata": {"query": query, "zip_path": zip_path},
            "domain_tags": ["3d_material", "rendering"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_unpaywall_enrich(con: sqlite3.Connection, limit: int = 20) -> int:
    email = (
        os.getenv("UNPAYWALL_EMAIL")
        or os.getenv("CROSSREF_MAILTO")
        or os.getenv("Materials_Project_ID")
        or "y.suzuki.hk@gmail.com"
    )
    rows = con.execute(
        """
        SELECT external_id, title, source, metadata_json
        FROM public_api_acquisitions
        WHERE source IN ('crossref', 'datacite', 'semantic_scholar', 'openalex')
          AND (local_path IS NULL OR local_path = '')
          AND external_id IS NOT NULL AND external_id != ''
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    count = 0
    seen: set[str] = set()
    for ext_id, title, src, meta_raw in rows:
        doi = _normalize_doi(ext_id)
        if not doi and meta_raw:
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = {}
            doi = _normalize_doi((meta.get("doi") or "") if isinstance(meta, dict) else "")
        if not doi or doi in seen:
            continue
        seen.add(doi)
        try:
            url = (
                f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}"
                f"?email={urllib.parse.quote(email)}"
            )
            data = http_get_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            continue
        except Exception:
            continue
        if not data.get("is_oa"):
            continue
        oa = data.get("best_oa_location") or {}
        pdf_url = oa.get("url_for_pdf") or ""
        if not pdf_url and (oa.get("url") or "").lower().endswith(".pdf"):
            pdf_url = oa.get("url") or ""
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        if pdf_url:
            safe = hashlib.sha1(doi.encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "unpaywall" / f"{safe}.pdf"
            if download_url(pdf_url, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
        row = {
            "acquired_at": now_jst(),
            "source": "unpaywall",
            "external_id": doi,
            "title": data.get("title") or title or doi,
            "url": pdf_url or f"https://doi.org/{doi}",
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": oa.get("license") or "Unpaywall OA location; verify publisher license",
            "metadata": {
                "enriched_from": src,
                "is_oa": data.get("is_oa"),
                "oa_status": data.get("oa_status"),
                "host_type": oa.get("host_type"),
                "pdf_url": pdf_url,
            },
            "domain_tags": ["research", "open_access"],
        }
        record_acquisition(con, row)
        count += 1
        time.sleep(0.5)
    return count


def harvest_patentsview(con: sqlite3.Connection, query: str) -> int:
    body = {
        "q": {"_text_any": {"patent_title": query}},
        "f": ["patent_id", "patent_title", "patent_date", "patent_abstract"],
        "o": {"per_page": 5},
    }
    data: dict = {}
    try:
        data = http_post_json("https://search.patentsview.org/api/v1/patent/", body)
    except Exception:
        legacy = {
            "q": {"_text_any": {"patent_title": query}},
            "f": ["patent_number", "patent_title", "patent_date", "patent_abstract"],
            "o": {"per_page": 5},
        }
        try:
            data = http_post_json("https://api.patentsview.org/patents/query", legacy)
        except Exception:
            return 0
    count = 0
    patents = data.get("patents") or []
    if isinstance(patents, dict):
        patents = patents.get("patents") or []
    for item in patents[:5]:
        if not isinstance(item, dict):
            continue
        patent_id = str(item.get("patent_id") or item.get("patent_number") or "")
        title = item.get("patent_title") or "untitled"
        page_url = f"https://patents.google.com/patent/US{patent_id}" if patent_id else ""
        row = {
            "acquired_at": now_jst(),
            "source": "patentsview",
            "external_id": patent_id,
            "title": title,
            "url": page_url,
            "local_path": None,
            "status": "metadata_only",
            "license_note": "USPTO PatentsView metadata; public domain government data",
            "metadata": {
                "query": query,
                "patent_date": item.get("patent_date"),
                "abstract": (item.get("patent_abstract") or "")[:500],
            },
            "domain_tags": ["patent", "manufacturing"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_crossref(con: sqlite3.Connection, query: str) -> int:
    mailto = os.getenv("CROSSREF_MAILTO") or os.getenv("Materials_Project_ID") or "y.suzuki.hk@gmail.com"
    params = urllib.parse.urlencode({"query": query, "rows": 5, "mailto": mailto})
    headers = {"User-Agent": f"ClawstackBot/1.0 (mailto:{mailto})"}
    data = http_get_json(f"https://api.crossref.org/works?{params}", headers=headers)
    count = 0
    for item in (data.get("message", {}).get("items") or [])[:5]:
        title = (item.get("title") or ["untitled"])[0]
        doi = item.get("DOI") or ""
        row = {
            "acquired_at": now_jst(),
            "source": "crossref",
            "external_id": doi,
            "title": title,
            "url": f"https://doi.org/{doi}" if doi else "",
            "local_path": None,
            "status": "metadata_only",
            "license_note": "Crossref metadata only",
            "metadata": {"query": query, "publisher": item.get("publisher"), "type": item.get("type")},
            "domain_tags": ["research"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_arxiv(con: sqlite3.Connection, query: str) -> int:
    params = urllib.parse.urlencode(
        {"search_query": f"all:{query}", "max_results": 3, "sortBy": "relevance"}
    )
    req = urllib.request.Request(
        f"https://export.arxiv.org/api/query?{params}",
        headers={"User-Agent": "ClawstackPublicApiHarvest/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_text = resp.read().decode("utf-8", errors="replace")
    root = ET.fromstring(xml_text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    count = 0
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        ext_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
        pdf_url = ""
        for link in entry.findall("a:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href") or ""
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        if pdf_url:
            safe = hashlib.sha1(ext_id.encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "arxiv" / f"{safe}.pdf"
            if download_url(pdf_url, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
        row = {
            "acquired_at": now_jst(),
            "source": "arxiv",
            "external_id": ext_id,
            "title": title,
            "url": ext_id,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "arXiv preprint; check arXiv license",
            "metadata": {"query": query, "pdf_url": pdf_url},
            "domain_tags": ["research", "ml"],
        }
        record_acquisition(con, row)
        count += 1
    time.sleep(3)
    return count


def harvest_jstage(con: sqlite3.Connection, query: str) -> int:
    path_q = urllib.parse.quote(query)
    url = f"https://api.jstage.jst.go.jp/searchapi/do?service=3&count=5&keyword={path_q}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ClawstackPublicApiHarvest/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0

    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return 0

    ns = {"a": "http://www.w3.org/2005/Atom"}
    count = 0
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        page_url = ""
        pdf_url = ""
        for link in entry.findall("a:link", ns):
            href = link.get("href") or ""
            if "_pdf" in href.lower() or link.get("type") == "application/pdf" or link.get("title") == "pdf":
                pdf_url = href
            elif "_article" in href.lower() or not page_url:
                page_url = href

        ext_id = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
        doi = _normalize_doi(ext_id) if "doi.org" in ext_id or "10." in ext_id else ""
        if not page_url:
            page_url = ext_id

        if not pdf_url and "_article" in page_url:
            pdf_url = page_url.replace("_article", "_pdf")

        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"

        if pdf_url:
            safe = hashlib.sha1(pdf_url.encode()).hexdigest()[:12]
            dest = DOWNLOAD_ROOT / "jstage" / f"{safe}.pdf"
            if download_url(pdf_url, dest):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"

        row = {
            "acquired_at": now_jst(),
            "source": "jstage",
            "external_id": doi or ext_id,
            "title": title,
            "url": page_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "J-STAGE OA article; verify publisher license",
            "metadata": {"query": query, "pdf_url": pdf_url, "doi": doi},
            "domain_tags": ["research", "manufacturing"],
        }
        record_acquisition(con, row)
        count += 1
    time.sleep(2)
    return count


def harvest_zenodo(con: sqlite3.Connection, query: str) -> int:
    token = os.getenv("ZENODO_ACCESS_TOKEN") or os.getenv("ZENODO_API") or ""
    params = urllib.parse.urlencode({"q": query, "size": 5, "sort": "bestmatch"})
    headers = {"User-Agent": "ClawstackPublicApiHarvest/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = http_get_json(f"https://zenodo.org/api/records?{params}", headers=headers)
    count = 0
    for hit in (data.get("hits", {}).get("hits") or [])[:5]:
        meta = hit.get("metadata") or {}
        title = meta.get("title") or "untitled"
        rec_id = str(hit.get("id") or "")
        rec_url = hit.get("links", {}).get("self_html") or f"https://zenodo.org/records/{rec_id}"
        files = hit.get("files") or []
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        for f in files:
            size = int(f.get("size") or 0)
            if size <= 0 or size > MAX_FILE_MB * 1024 * 1024:
                continue
            dl = f.get("links", {}).get("self") or f.get("links", {}).get("download")
            if not dl:
                continue
            fname = f.get("key") or f"zenodo_{rec_id}.bin"
            dest = DOWNLOAD_ROOT / "zenodo" / rec_id / fname
            if dest.exists() and dest.stat().st_size > 0:
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded_existing"
                break
            if download_url(dl, dest, headers=headers):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
                break
        row = {
            "acquired_at": now_jst(),
            "source": "zenodo",
            "external_id": rec_id,
            "title": title,
            "url": rec_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": _license_str(meta.get("license")) or "Check Zenodo record license",
            "metadata": {"query": query, "file_count": len(files), "doi": meta.get("doi")},
            "domain_tags": ["dataset", "cae"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def http_post_json(url: str, body: dict, headers: dict | None = None, timeout: int = 30) -> dict | list:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            **(headers or {}),
            "Content-Type": "application/json",
            "User-Agent": "ClawstackPublicApiHarvest/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def harvest_figshare(con: sqlite3.Connection, query: str) -> int:
    token = os.getenv("FIGSHARE_API_TOKEN") or os.getenv("Figshare_API") or ""
    headers = {"User-Agent": "ClawstackPublicApiHarvest/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    items = http_post_json(
        "https://api.figshare.com/v2/articles/search",
        {"search_for": query, "page_size": 5, "item_type": 3},
        headers=headers,
    )
    count = 0
    for item in (items if isinstance(items, list) else [])[:5]:
        art_id = str(item.get("id") or "")
        title = item.get("title") or "untitled"
        page_url = item.get("url_public_html") or f"https://figshare.com/articles/dataset/_/{art_id}"
        detail = http_get_json(f"https://api.figshare.com/v2/articles/{art_id}", headers=headers)
        files = detail.get("files") or []
        local_path = None
        size_bytes = None
        digest = None
        status = "metadata_only"
        for f in files:
            size = int(f.get("size") or 0)
            if size <= 0 or size > MAX_FILE_MB * 1024 * 1024:
                continue
            dl = f.get("download_url")
            if not dl:
                continue
            fname = f.get("name") or f"figshare_{art_id}.bin"
            dest = DOWNLOAD_ROOT / "figshare" / art_id / fname
            if dest.exists() and dest.stat().st_size > 0:
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded_existing"
                break
            if download_url(dl, dest, headers=headers):
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
                status = "downloaded"
                break
        row = {
            "acquired_at": now_jst(),
            "source": "figshare",
            "external_id": art_id,
            "title": title,
            "url": page_url,
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": _license_str(detail.get("defined_type_name")) or "Check Figshare license",
            "metadata": {"query": query, "doi": detail.get("doi"), "file_count": len(files)},
            "domain_tags": ["dataset"],
        }
        record_acquisition(con, row)
        count += 1
    return count


def harvest_github_search(con: sqlite3.Connection, query: str) -> int:
    token = (os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT") or "").strip()
    headers = {
        "User-Agent": "ClawstackPublicApiHarvest/1.0",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    q = urllib.parse.quote(f"{query} stars:>10")
    data = http_get_json(
        f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=3",
        headers=headers,
    )
    count = 0
    gh_dir = DOWNLOAD_ROOT / "github"
    gh_dir.mkdir(parents=True, exist_ok=True)
    for repo in (data.get("items") or [])[:2]:
        full = repo.get("full_name") or ""
        branch = repo.get("default_branch") or "main"
        zip_url = f"https://github.com/{full}/archive/refs/heads/{branch}.zip"
        safe = full.replace("/", "_") + f"_{branch}.zip"
        dest = gh_dir / safe
        status = "metadata_only"
        local_path = None
        size_bytes = None
        digest = None
        if not dest.exists():
            if download_url(zip_url, dest, headers=headers):
                status = "downloaded"
                local_path = dest.relative_to(ROOT).as_posix()
                size_bytes = dest.stat().st_size
                digest = sha256_file(dest)
        else:
            status = "downloaded_existing"
            local_path = dest.relative_to(ROOT).as_posix()
            size_bytes = dest.stat().st_size
            digest = sha256_file(dest)
        row = {
            "acquired_at": now_jst(),
            "source": "github",
            "external_id": full,
            "title": repo.get("description") or full,
            "url": repo.get("html_url") or "",
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": repo.get("license", {}).get("spdx_id") if isinstance(repo.get("license"), dict) else "",
            "metadata": {
                "query": query,
                "stars": repo.get("stargazers_count"),
                "language": repo.get("language"),
            },
            "domain_tags": ["opensource", "factory"],
        }
        record_acquisition(con, row)
        count += 1
        time.sleep(1)
    return count


def harvest_roboflow(con: sqlite3.Connection) -> int:
    key = os.getenv("ROBOFLOW_API_KEY") or os.getenv("Roboflow_API") or ""
    if not key:
        return 0
    url = "https://api.roboflow.com/?" + urllib.parse.urlencode({"api_key": key})
    data = http_get_json(url)
    workspace = data.get("workspace") or data.get("workspaceName") or "unknown"
    count = 0
    row = {
        "acquired_at": now_jst(),
        "source": "roboflow",
        "external_id": workspace,
        "title": f"Roboflow workspace {workspace}",
        "url": "https://app.roboflow.com/",
        "local_path": None,
        "status": "metadata_only",
        "license_note": "Per-project license on export",
        "metadata": {"workspace": workspace, "welcome": data.get("welcome")},
        "domain_tags": ["vision", "defect"],
    }
    record_acquisition(con, row)
    count += 1
    candidates_path = WORKSPACE / "apps" / "growth_dashboard" / "roboflow_candidate_datasets.json"
    if candidates_path.exists():
        cand = json.loads(candidates_path.read_text(encoding="utf-8-sig"))
        for item in (cand.get("items") or [])[:MAX_PER_SOURCE]:
            row = {
                "acquired_at": now_jst(),
                "source": "roboflow_candidate",
                "external_id": item.get("slug"),
                "title": item.get("dataset"),
                "url": item.get("url"),
                "local_path": None,
                "status": "queued_license_review",
                "license_note": "Export after user license review",
                "metadata": item,
                "domain_tags": ["vision", "defect"],
            }
            record_acquisition(con, row)
            count += 1
    return count


def _kaggle_cmd() -> list[str]:
    return [sys.executable, "-m", "kaggle"]


def harvest_kaggle(con: sqlite3.Connection, query: str) -> int:
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        return 0
    try:
        proc = subprocess.run(
            _kaggle_cmd() + ["datasets", "list", "-s", query, "--sort-by", "hottest", "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except FileNotFoundError:
        return 0
    if proc.returncode != 0:
        return 0
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip() and not ln.startswith("ref")]
    count = 0
    for line in lines[:3]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        ref = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ref
        dest_dir = DOWNLOAD_ROOT / "kaggle" / ref.replace("/", "_")
        status = "metadata_only"
        local_path = None
        size_bytes = None
        digest = None
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            dl = subprocess.run(
                _kaggle_cmd() + ["datasets", "download", "-d", ref, "-p", str(dest_dir), "--unzip"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if dl.returncode == 0:
                status = "downloaded"
                local_path = dest_dir.relative_to(ROOT).as_posix()
                size_bytes = sum(f.stat().st_size for f in dest_dir.rglob("*") if f.is_file())
        else:
            status = "downloaded_existing"
            local_path = dest_dir.relative_to(ROOT).as_posix()
            size_bytes = sum(f.stat().st_size for f in dest_dir.rglob("*") if f.is_file())
        row = {
            "acquired_at": now_jst(),
            "source": "kaggle",
            "external_id": ref,
            "title": title,
            "url": f"https://www.kaggle.com/datasets/{ref}",
            "local_path": local_path,
            "size_bytes": size_bytes,
            "sha256": digest,
            "status": status,
            "license_note": "Review Kaggle dataset license before production use",
            "metadata": {"query": query},
            "domain_tags": ["dataset", "ml"],
        }
        record_acquisition(con, row)
        count += 1
        if count >= 2:
            break
    return count


def harvest_materials_project(con: sqlite3.Connection) -> int:
    script = ROOT / "scripts" / "cae_scraper" / "scraper_materials_project.py"
    if not script.exists():
        return 0
    proc = subprocess.run(
        [sys.executable, str(script), "--presets", "--max", "3"],
        cwd=str(script.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    mp_dir = ROOT / "data" / "cae_downloads" / "materials_project"
    count = 0
    if mp_dir.exists():
        for path in sorted(mp_dir.glob("mp_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            label = path.stem
            material_count = 0
            if isinstance(meta, dict):
                label = meta.get("label") or label
                materials = meta.get("materials")
                material_count = len(materials) if isinstance(materials, list) else 0
            elif isinstance(meta, list):
                material_count = len(meta)
            row = {
                "acquired_at": now_jst(),
                "source": "materials_project",
                "external_id": path.stem,
                "title": label,
                "url": "https://materialsproject.org/",
                "local_path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "status": "downloaded" if proc.returncode == 0 else "downloaded_existing",
                "license_note": "Materials Project terms of use",
                "metadata": {
                    "material_count": material_count,
                    "stdout_tail": (proc.stdout or "")[-400:],
                },
                "domain_tags": ["materials", "cae", "openradioss"],
            }
            record_acquisition(con, row)
            count += 1
    return count


def _merged_search_queries() -> list[str]:
    merged = list(SEARCH_QUERIES)
    try:
        sys.path.insert(0, str(WORKSPACE))
        import harvest_query_optimizer as query_opt

        general = (query_opt.build_learned_queries().get("domains") or {}).get("general", {})
        for q in general.get("prioritized_queries") or []:
            text = str(q).strip()
            if text and text not in merged:
                merged.insert(0, text)
    except Exception:
        pass
    return merged[:MAX_PER_SOURCE]


def _source_handlers(con: sqlite3.Connection, query: str) -> dict[str, Any]:
    return {
        "openalex": lambda: harvest_openalex(con, query),
        "crossref": lambda: harvest_crossref(con, query),
        "datacite": lambda: harvest_datacite(con, query),
        "europe_pmc": lambda: harvest_europe_pmc(con, query),
        "semantic_scholar": lambda: harvest_semantic_scholar(con, query),
        "doaj": lambda: harvest_doaj(con, query),
        "arxiv": lambda: harvest_arxiv(con, query),
        "jstage": lambda: harvest_jstage(con, query),
        "zenodo": lambda: harvest_zenodo(con, query),
        "figshare": lambda: harvest_figshare(con, query),
        "github": lambda: harvest_github_search(con, query),
        "huggingface_datasets": lambda: harvest_huggingface_datasets(con, query),
    }


def run_harvest(
    *,
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    include_extras: bool = True,
    inter_delay: float = 0.5,
) -> dict[str, Any]:
    load_env()
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    con = ensure_db()
    stats: dict[str, int] = {}
    errors: list[str] = []

    query_list = list(queries or _merged_search_queries())
    handlers = _source_handlers(con, "")
    active_sources = list(sources) if sources else list(handlers.keys())

    for q in query_list:
        per_query = _source_handlers(con, q)
        for name in active_sources:
            fn = per_query.get(name)
            if not fn:
                continue
            try:
                n = fn()
                stats[name] = stats.get(name, 0) + n
            except Exception as exc:
                errors.append(f"{name}:{q}:{exc}")
            time.sleep(max(0.2, inter_delay))

    if include_extras and not sources:
        for aq in ("metal", "plastic", "fabric", "concrete"):
            try:
                n = harvest_ambientcg(con, aq)
                stats["ambientcg"] = stats.get("ambientcg", 0) + n
            except Exception as exc:
                errors.append(f"ambientcg:{aq}:{exc}")
            time.sleep(max(0.2, inter_delay))

        for pq in (
            "progressive die",
            "injection mold",
            "sheet metal stamping",
        ):
            try:
                n = harvest_patentsview(con, pq)
                stats["patentsview"] = stats.get("patentsview", 0) + n
            except Exception as exc:
                errors.append(f"patentsview:{pq}:{exc}")
            time.sleep(max(0.2, inter_delay))

        try:
            n = harvest_unpaywall_enrich(con, limit=20)
            stats["unpaywall"] = stats.get("unpaywall", 0) + n
        except Exception as exc:
            errors.append(f"unpaywall:{exc}")

        for name, fn in (
            ("roboflow", lambda: harvest_roboflow(con)),
            ("materials_project", lambda: harvest_materials_project(con)),
        ):
            try:
                n = fn()
                stats[name] = stats.get(name, 0) + n
            except Exception as exc:
                errors.append(f"{name}:{exc}")

        for kq in (
            "surface defect manufacturing",
            "steel defect detection",
            "injection molding dataset",
            "metal stamping",
            "quality inspection image",
        ):
            try:
                n = harvest_kaggle(con, kq)
                stats["kaggle"] = stats.get("kaggle", 0) + n
            except Exception as exc:
                errors.append(f"kaggle:{kq}:{exc}")
            time.sleep(max(0.5, inter_delay))

    total = sum(stats.values())
    status = {
        "updated_at": now_jst(),
        "total_records": total,
        "by_source": stats,
        "download_root": DOWNLOAD_ROOT.relative_to(ROOT).as_posix(),
        "manifest_jsonl": MANIFEST_JSONL.relative_to(ROOT).as_posix(),
        "growth_db": GROWTH_DB.relative_to(ROOT).as_posix(),
        "errors": errors[:20],
        "slice_mode": bool(sources or (queries and len(queries) < len(SEARCH_QUERIES))),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    con.close()
    try:
        sys.path.insert(0, str(WORKSPACE))
        import harvest_query_optimizer as query_opt

        query_opt.write_report()
    except Exception:
        pass

    export_script = ROOT / "scripts" / "export_material_source_inventory.py"
    if export_script.exists():
        import subprocess

        subprocess.run([sys.executable, str(export_script)], cwd=str(ROOT), check=False)
    return status


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Harvest metadata/files from public APIs")
    parser.add_argument("--sources", nargs="*", help="Limit to these sources (slice mode)")
    parser.add_argument("--queries", nargs="*", help="Explicit query list")
    parser.add_argument("--max-queries", type=int, default=0, help="Limit query count from merged list")
    parser.add_argument("--query-offset", type=int, default=0, help="Rotate merged queries")
    parser.add_argument("--skip-extras", action="store_true", help="Skip ambientcg/patents/kaggle extras")
    parser.add_argument("--inter-delay", type=float, default=0.5, help="Seconds between API calls")
    args = parser.parse_args()

    queries = list(args.queries) if args.queries else _merged_search_queries()
    if args.query_offset:
        off = max(0, args.query_offset)
        queries = queries[off:] + queries[:off]
    if args.max_queries and args.max_queries > 0:
        queries = queries[: args.max_queries]

    status = run_harvest(
        queries=queries,
        sources=args.sources,
        include_extras=not args.skip_extras,
        inter_delay=max(0.2, args.inter_delay),
    )
    total = int(status.get("total_records") or 0)
    stats = status.get("by_source") or {}
    print(f"[OK] public_api_bulk_harvest total_records={total}")
    print(f"[OK] by_source={json.dumps(stats, ensure_ascii=False)}")
    print(f"[OK] status={STATUS_PATH}")
    if status.get("errors"):
        errs = status["errors"]
        print(f"[WARN] errors={len(errs)} first={errs[0][:120]}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
