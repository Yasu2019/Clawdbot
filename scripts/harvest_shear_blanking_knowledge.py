# -*- coding: utf-8 -*-
"""Harvest worldwide shear-blanking knowledge into universal_growth.db, mojibake-free.

Scope is bounded to what INC-188 is blocked on: a defensible material calibration
for the 4-body (punch / stripper / blank / die) blanking model.

Encoding contract: bytes -> declared charset -> strict decode -> codepoint
validation -> UTF-8 SQLite -> read-back + SHA256 comparison. Console rendering is
never used as evidence; only codepoints are.
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "workspace" / "universal_growth.db"
CORPUS_DIR = Path("F:/clawstack_data/shear_blanking_corpus")
CONTACT = "yasuhiro-suzuki@mitsui-s.com"
USER_AGENT = f"Clawstack-CAE-Knowledge/2.0 (bounded research; mailto:{CONTACT})"

# U+FFFD plus the CP932-read-as-UTF-8 and UTF-8-read-as-CP932 signatures.
MOJIBAKE_MARKERS = ("\ufffd", "縺", "繧", "繝", "譁", "蜈", "ãƒ", "â€", "Ã¯Â¿Â½")

CATEGORIES = {
    # The part is MR536, an AA5052 base. The deck's "1060" label is a known defect;
    # 1060 queries stay only to document why that label was rejected.
    "material_constants": [
        "AA5052 aluminium Johnson-Cook constitutive parameters flow stress",
        "5052 aluminium alloy fracture locus stress triaxiality damage",
        "5052-H32 aluminium sheet tensile temper mechanical properties",
        "Al-Mg 5052 sheet forming limit ductile fracture criterion",
        "AA1060 aluminum Johnson-Cook constitutive parameters",
    ],
    "ductile_failure": [
        "ductile fracture criterion metal blanking prediction",
        "Cockcroft-Latham critical damage value sheet metal shearing",
        "uncoupled damage model blanking fracture calibration",
    ],
    "blanking_process": [
        "blanking clearance cut edge quality rollover burnish fracture burr",
        "fine blanking finite element simulation process parameters",
        "progressive die stamping simulation part quality",
    ],
    "numerical_setup": [
        "element deletion adaptive remeshing blanking simulation shear band",
        "sheet metal shearing explicit finite element mesh through thickness",
    ],
    # --- 2026-08-11 追加。INC-188 の実際の壁に的を絞る ---------------------
    # 症状: 破断しきい値に達しても切断輪郭の亀裂が板厚を貫通せず、スラグが分離しない。
    # 3Dでメッシュを8倍にしても輪郭破断は伸びなかった(9.3%->6.7%)。
    "crack_propagation_failure": [
        "crack propagation blanking simulation slug separation not achieved",
        "through thickness crack blanking finite element element erosion",
        "shear band localization mesh size dependence blanking",
        "damage localization regularization non-local blanking simulation",
    ],
    # 荷重-ストロークから破断パラメータを逆同定する手法。RCA が要求している校正。
    "inverse_calibration": [
        "inverse identification ductile damage parameters force displacement blanking",
        "punch force stroke curve calibration fracture model sheet metal",
        "parameter identification Johnson-Cook damage shear test optimization",
    ],
    # Radioss 固有。GENE1 のしきい値や要素削除の挙動。
    "radioss_specific": [
        "Radioss FAIL GENE1 element deletion solid failure criterion",
        "OpenRadioss blanking shearing tutorial example model",
        "Radioss 2D plane strain axisymmetric forming simulation",
    ],
    # クリアランスの定量的影響。今回まさに真因だった箇所。
    "clearance_quantitative": [
        "blanking clearance percentage sheet thickness optimum aluminium",
        "punch die clearance effect fracture angle burnish ratio",
    ],
}

# Directly reachable official documentation (verified 200 before coding in).
DIRECT_DOCS = (
    {
        "id": "altair-fail-johnson",
        "title": "Radioss /FAIL/JOHNSON",
        "url": "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/fail_johnson_starter_r.htm",
        "publisher": "Altair",
        "category": "solver_reference",
    },
    {
        "id": "altair-fail-gene1",
        "title": "Radioss /FAIL/GENE1",
        "url": "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/fail_gene1_starter_r.htm",
        "publisher": "Altair",
        "category": "solver_reference",
    },
    {
        "id": "altair-results-checking",
        "title": "Radioss results checking",
        "url": "https://2025.help.altair.com/2025/hwsolvers/rad/topics/solvers/rad/faq_rad_results_checking_r.htm",
        "publisher": "Altair",
        "category": "solver_reference",
    },
)

GITHUB_REPOS = ("OpenRadioss/OpenRadioss", "OpenRadioss/ModelExchange", "OpenRadioss/Tools")

# Constants actually recovered from reachable sources, each with its provenance and an
# explicit verdict on whether it may be used to calibrate the INC-188 deck.
# usable=0 means: informative, but NOT sufficient to justify a solver run.
MAKEITFROM_O = "https://www.makeitfrom.com/material-properties/1060-O-Aluminum"
MAKEITFROM_H18 = "https://www.makeitfrom.com/material-properties/1060-H18-Aluminum"
PMC_BLANKING = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11066666/"

MAKEITFROM_5052_O = "https://www.makeitfrom.com/material-properties/5052-O-Aluminum"
MAKEITFROM_5052_H32 = "https://www.makeitfrom.com/material-properties/5052-H32-Aluminum"

EXTRACTED_CALIBRATION = (
    # MR536 is an AA5052 base (user-supplied, 2026-08-11). These are the rows that
    # actually describe the part; the AA1060 rows below are kept as audit trail only.
    ("AA5052", "O", "elastic", "youngs_modulus", 68e9, "Pa", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "elastic", "shear_modulus", 26e9, "Pa", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "elastic", "poisson_ratio", 0.33, "-", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "strength", "tensile_yield", 79e6, "Pa", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "strength", "ultimate_tensile", 190e6, "Pa", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "strength", "shear_strength", 130e6, "Pa", MAKEITFROM_5052_O, "secondary_screening", 1),
    ("AA5052", "O", "ductility", "elongation_at_break", 0.22, "-", MAKEITFROM_5052_O, "secondary_screening", 0),
    ("AA5052", "H32", "elastic", "youngs_modulus", 68e9, "Pa", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "elastic", "shear_modulus", 26e9, "Pa", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "elastic", "poisson_ratio", 0.33, "-", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "strength", "tensile_yield", 180e6, "Pa", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "strength", "ultimate_tensile", 230e6, "Pa", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "strength", "shear_strength", 140e6, "Pa", MAKEITFROM_5052_H32, "secondary_screening", 1),
    ("AA5052", "H32", "ductility", "elongation_at_break", 0.12, "-", MAKEITFROM_5052_H32, "secondary_screening", 0),
    ("AA1060", "O", "elastic", "youngs_modulus", 68e9, "Pa", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "elastic", "shear_modulus", 26e9, "Pa", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "elastic", "poisson_ratio", 0.33, "-", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "strength", "tensile_yield", 21e6, "Pa", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "strength", "ultimate_tensile", 72e6, "Pa", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "strength", "shear_strength", 49e6, "Pa", MAKEITFROM_O, "secondary_screening", 1),
    ("AA1060", "O", "ductility", "elongation_at_break", 0.30, "-", MAKEITFROM_O, "secondary_screening", 0),
    ("AA1060", "H18", "elastic", "youngs_modulus", 68e9, "Pa", MAKEITFROM_H18, "secondary_screening", 1),
    ("AA1060", "H18", "strength", "tensile_yield", 110e6, "Pa", MAKEITFROM_H18, "secondary_screening", 1),
    ("AA1060", "H18", "strength", "ultimate_tensile", 130e6, "Pa", MAKEITFROM_H18, "secondary_screening", 1),
    ("AA1060", "H18", "strength", "shear_strength", 75e6, "Pa", MAKEITFROM_H18, "secondary_screening", 1),
    ("AA1060", "H18", "ductility", "elongation_at_break", 0.04, "-", MAKEITFROM_H18, "secondary_screening", 0),
    # Method reference only. DP600 constants must never be transplanted onto AA1060.
    ("DP600", "as-received", "swift_hardening", "K", 950.459e6, "Pa", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "swift_hardening", "eps0", 0.002036, "-", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "swift_hardening", "n", 0.154, "-", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "MMC3_fracture", "C1", 0.02, "-", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "MMC3_fracture", "C2", 465.07e6, "Pa", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "MMC3_fracture", "C3", 0.97, "-", PMC_BLANKING, "peer_reviewed_open_access", 0),
    ("DP600", "as-received", "contact", "coulomb_friction", 0.15, "-", PMC_BLANKING, "peer_reviewed_open_access", 0),
)

CALIBRATION_NOTES = {
    1: "Traceable screening value. Sufficient to reject the untraceable deck card; "
       "not sufficient on its own to calibrate ductile damage.",
    0: "Reference only. Either a uniaxial ductility value that does not transfer to the "
       "blanking shear zone, or another alloy's constants that must not be transplanted.",
}


class MojibakeError(ValueError):
    """Raised when text fails the codepoint-level cleanliness contract."""


def validate_text(text: str, where: str) -> str:
    """Fail closed on corruption. Judged by codepoints, never by console output."""
    hits = [m for m in MOJIBAKE_MARKERS if m in text]
    if hits:
        raise MojibakeError(f"{where}: mojibake markers {hits!r}")
    if text.encode("utf-8").decode("utf-8") != text:
        raise MojibakeError(f"{where}: UTF-8 round-trip mismatch")
    return text


def _charset_from(headers, body: bytes) -> str:
    declared = ""
    ctype = headers.get("Content-Type", "") if headers else ""
    match = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if match:
        declared = match.group(1)
    if not declared:
        match = re.search(rb'charset=["\']?([\w\-]+)', body[:4096], re.I)
        if match:
            declared = match.group(1).decode("ascii", errors="ignore")
    return (declared or "utf-8").lower().replace("shift_jis", "cp932").replace("sjis", "cp932")


def fetch(url: str, timeout: int = 40, limit: int = 4_000_000) -> tuple[int, str, str, bytes]:
    """Return (status, final_url, decoded_text, raw_bytes) with strict decoding."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(limit)
                status, final_url = int(response.status), response.geturl()
                charset = _charset_from(response.headers, raw)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503) or attempt == 3:
                raise
            time.sleep(2 ** attempt * 3)
    else:  # pragma: no cover - loop always breaks or raises
        raise MojibakeError(f"{url}: unreachable")
    for candidate in (charset, "utf-8", "cp932", "euc_jp", "latin-1"):
        try:
            text = raw.decode(candidate, errors="strict")
        except (UnicodeDecodeError, LookupError):
            continue
        if candidate == "latin-1" and charset != "latin-1":
            continue
        return status, final_url, text, raw
    raise MojibakeError(f"{url}: no strict decoding succeeded (declared {charset})")


def fetch_json(url: str) -> dict:
    _, _, text, _ = fetch(url)
    return json.loads(text)


def _strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()


def _openalex_abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, spots in inverted.items():
        positions.extend((spot, word) for spot in spots)
    return " ".join(word for _, word in sorted(positions))


def _record(**kw) -> dict:
    kw.setdefault("authors", "")
    kw.setdefault("year", None)
    kw.setdefault("doi", "")
    kw.setdefault("oa_url", "")
    kw.setdefault("language", "en")
    kw.setdefault("abstract", "")
    kw.setdefault("license_note", "")
    return kw


def harvest_openalex(query: str, category: str, rows: int) -> list[dict]:
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(query)
           + f"&per_page={rows}&mailto=" + urllib.parse.quote(CONTACT))
    out = []
    for work in fetch_json(url).get("results", []):
        oa = work.get("open_access") or {}
        is_oa = bool(oa.get("is_oa"))
        out.append(_record(
            source_id="openalex:" + str(work.get("id", "")).rsplit("/", 1)[-1],
            provider="OpenAlex",
            category=category,
            query=query,
            title=work.get("display_name") or "",
            authors="; ".join(
                (a.get("author") or {}).get("display_name", "")
                for a in (work.get("authorships") or [])[:8]
            ),
            year=work.get("publication_year"),
            doi=(work.get("doi") or "").replace("https://doi.org/", ""),
            url=work.get("id") or "",
            oa_url=oa.get("oa_url") or "",
            publisher=((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
            access_class="open_access" if is_oa else "paid_or_subscription",
            license_note=(work.get("primary_location") or {}).get("license")
                         or ("open access" if is_oa else "metadata only; full text not downloaded"),
            abstract=_openalex_abstract(work.get("abstract_inverted_index")),
        ))
    return out


def harvest_crossref(query: str, category: str, rows: int) -> list[dict]:
    url = ("https://api.crossref.org/works?query=" + urllib.parse.quote(query)
           + f"&rows={rows}&mailto=" + urllib.parse.quote(CONTACT))
    out = []
    for item in fetch_json(url)["message"]["items"]:
        licenses = [l.get("URL", "") for l in item.get("license") or []]
        out.append(_record(
            source_id="crossref:" + item.get("DOI", ""),
            provider="Crossref",
            category=category,
            query=query,
            title=(item.get("title") or [""])[0],
            authors="; ".join(
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (item.get("author") or [])[:8]
            ),
            year=(item.get("issued", {}).get("date-parts") or [[None]])[0][0],
            doi=item.get("DOI", ""),
            url="https://doi.org/" + item.get("DOI", ""),
            publisher=item.get("publisher", ""),
            access_class="open_access" if licenses else "paid_or_subscription",
            license_note="; ".join(licenses) or "metadata only; full text not downloaded",
            abstract=_strip_tags(item.get("abstract", "")),
        ))
    return out


def harvest_europepmc(query: str, category: str, rows: int) -> list[dict]:
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
           + urllib.parse.quote(query) + f"&format=json&pageSize={rows}")
    out = []
    for item in fetch_json(url).get("resultList", {}).get("result", []):
        is_oa = item.get("isOpenAccess") == "Y"
        pmcid = item.get("pmcid", "")
        out.append(_record(
            source_id="europepmc:" + (pmcid or item.get("id", "")),
            provider="EuropePMC",
            category=category,
            query=query,
            title=item.get("title", ""),
            authors=item.get("authorString", ""),
            year=int(item["pubYear"]) if str(item.get("pubYear", "")).isdigit() else None,
            doi=item.get("doi", ""),
            url=f"https://europepmc.org/article/{item.get('source','MED')}/{item.get('id','')}",
            oa_url=f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid and is_oa else "",
            publisher=item.get("journalTitle", ""),
            access_class="open_access" if is_oa else "paid_or_subscription",
            license_note="open access" if is_oa else "metadata only; full text not downloaded",
            abstract=item.get("abstractText", ""),
        ))
    return out


def harvest_arxiv(query: str, category: str, rows: int) -> list[dict]:
    url = ("http://export.arxiv.org/api/query?search_query=all:"
           + urllib.parse.quote(f'"{query}"') + f"&max_results={rows}")
    _, _, xml, _ = fetch(url)
    out = []
    for entry in re.findall(r"(?s)<entry>(.*?)</entry>", xml):
        def tag(name: str) -> str:
            found = re.search(rf"(?s)<{name}>(.*?)</{name}>", entry)
            return re.sub(r"\s+", " ", found.group(1)).strip() if found else ""
        link = tag("id")
        out.append(_record(
            source_id="arxiv:" + link.rsplit("/", 1)[-1],
            provider="arXiv",
            category=category,
            query=query,
            title=tag("title"),
            authors="; ".join(re.findall(r"(?s)<name>(.*?)</name>", entry))[:400],
            year=int(tag("published")[:4]) if tag("published")[:4].isdigit() else None,
            url=link,
            oa_url=link.replace("/abs/", "/pdf/"),
            publisher="arXiv",
            access_class="open_access",
            license_note="arXiv open access",
            abstract=tag("summary"),
        ))
    return out


def harvest_jstage(article_query: str, category: str, rows: int) -> list[dict]:
    """Japanese primary literature. This path is the strictest mojibake test."""
    url = ("https://api.jstage.jst.go.jp/searchapi/do?service=3&article="
           + urllib.parse.quote(article_query) + f"&count={rows}")
    _, _, xml, _ = fetch(url)
    out = []
    for entry in re.findall(r"(?s)<entry>(.*?)</entry>", xml):
        def bilingual(name: str) -> tuple[str, str]:
            block = re.search(rf"(?s)<{name}>(.*?)</{name}>", entry)
            if not block:
                return "", ""
            body = block.group(1)
            def lang(code: str) -> str:
                found = re.search(rf"(?s)<{code}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{code}>", body)
                return found.group(1).strip() if found else ""
            return lang("ja"), lang("en")
        title_ja, title_en = bilingual("article_title")
        journal_ja, _ = bilingual("material_title")
        authors_ja, _ = bilingual("author")
        link = re.search(r"(?s)<article_link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</article_link>", entry)
        doi = re.search(r"<prism:doi>(.*?)</prism:doi>", entry)
        year = re.search(r"<prism:publicationDate>(\d{4})", entry)
        out.append(_record(
            source_id="jstage:" + (doi.group(1) if doi else hashlib.sha1(
                (title_ja or title_en).encode("utf-8")).hexdigest()[:16]),
            provider="J-STAGE",
            category=category,
            query=article_query,
            title=title_ja or title_en,
            authors=re.sub(r"<[^>]+>", " ", authors_ja).strip()[:400],
            year=int(year.group(1)) if year else None,
            doi=doi.group(1) if doi else "",
            url=(link.group(1).strip() if link else ""),
            publisher=journal_ja,
            language="ja",
            access_class="metadata_public",
            license_note="J-STAGE public metadata; full text per publisher terms",
            abstract=title_en,
        ))
    return out


def harvest_direct_docs() -> list[dict]:
    out = []
    for doc in DIRECT_DOCS:
        status, final_url, text, _ = fetch(doc["url"])
        body = _strip_tags(text)
        out.append(_record(
            source_id="doc:" + doc["id"],
            provider=doc["publisher"],
            category=doc["category"],
            query="official documentation",
            title=doc["title"],
            url=doc["url"],
            oa_url=final_url,
            publisher=doc["publisher"],
            access_class="direct_free",
            license_note=f"publicly accessible official documentation; copyright {doc['publisher']}",
            abstract=body[:6000],
            http_status=status,
        ))
    return out


def harvest_github() -> list[dict]:
    out = []
    for repo in GITHUB_REPOS:
        data = fetch_json(f"https://api.github.com/repos/{repo}")
        out.append(_record(
            source_id="github:" + repo,
            provider="GitHub",
            category="public_implementation",
            query="OpenRadioss reference implementation",
            title=data.get("full_name", repo),
            year=int(str(data.get("created_at", ""))[:4] or 0) or None,
            url=data.get("html_url", f"https://github.com/{repo}"),
            oa_url=f"https://github.com/{repo}",
            publisher="OpenRadioss",
            access_class="direct_free",
            license_note=((data.get("license") or {}).get("spdx_id") or "see repository"),
            abstract=(data.get("description") or "") + f" | stars={data.get('stargazers_count')}"
                     f" language={data.get('language')} topics={','.join(data.get('topics') or [])}",
        ))
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS shear_blanking_sources (
    source_id     TEXT PRIMARY KEY,
    harvested_at  TEXT NOT NULL,
    provider      TEXT NOT NULL,
    category      TEXT NOT NULL,
    query         TEXT NOT NULL,
    title         TEXT NOT NULL,
    authors       TEXT NOT NULL,
    year          INTEGER,
    doi           TEXT NOT NULL,
    url           TEXT NOT NULL,
    oa_url        TEXT NOT NULL,
    publisher     TEXT NOT NULL,
    language      TEXT NOT NULL,
    access_class  TEXT NOT NULL,
    license_note  TEXT NOT NULL,
    abstract      TEXT NOT NULL,
    http_status   INTEGER,
    content_sha256 TEXT NOT NULL,
    encoding      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shear_blanking_quarantine (
    source_id     TEXT PRIMARY KEY,
    quarantined_at TEXT NOT NULL,
    provider      TEXT NOT NULL,
    url           TEXT NOT NULL,
    reason        TEXT NOT NULL,
    field_repr    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shear_blanking_calibration (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    material      TEXT NOT NULL,
    temper        TEXT NOT NULL,
    model         TEXT NOT NULL,
    parameter     TEXT NOT NULL,
    value         REAL,
    unit          TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    source_url    TEXT NOT NULL,
    traceability  TEXT NOT NULL,
    usable_for_calibration INTEGER NOT NULL,
    note          TEXT NOT NULL,
    recorded_at   TEXT NOT NULL
);
"""


def ensure_schema(connection: sqlite3.Connection) -> str:
    connection.executescript(SCHEMA)
    for tokenizer in ("trigram", "unicode61"):
        try:
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS shear_blanking_fts USING fts5("
                "source_id UNINDEXED, title, authors, abstract, publisher, "
                f"tokenize='{tokenizer}')"
            )
            return tokenizer
        except sqlite3.OperationalError:
            continue
    return "none"


def write_rows(connection: sqlite3.Connection, records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Clean records go to the corpus; upstream-corrupted ones are quarantined, never written."""
    written, quarantined = [], []
    for rec in records:
        try:
            for field in ("title", "authors", "abstract", "publisher", "license_note"):
                validate_text(str(rec.get(field) or ""), f"{rec['source_id']}.{field}")
        except MojibakeError as exc:
            connection.execute(
                "INSERT OR REPLACE INTO shear_blanking_quarantine VALUES (?,?,?,?,?,?)",
                (rec["source_id"], datetime.now(timezone.utc).isoformat(), rec["provider"],
                 rec.get("url", ""), str(exc),
                 ascii(str(rec.get("authors") or rec.get("title") or ""))[:500]),
            )
            quarantined.append({"source_id": rec["source_id"], "reason": str(exc)})
            continue
        payload = json.dumps(
            {k: rec.get(k) for k in ("title", "authors", "abstract", "doi", "url")},
            ensure_ascii=False, sort_keys=True,
        )
        digest = hashlib.sha256(validate_text(payload, rec["source_id"]).encode("utf-8")).hexdigest()
        connection.execute(
            "INSERT OR REPLACE INTO shear_blanking_sources VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rec["source_id"], datetime.now(timezone.utc).isoformat(), rec["provider"],
             rec["category"], rec["query"], rec["title"], rec["authors"], rec["year"],
             rec["doi"], rec["url"], rec["oa_url"], rec["publisher"], rec["language"],
             rec["access_class"], rec["license_note"], rec["abstract"],
             rec.get("http_status"), digest, "utf-8"),
        )
        connection.execute("DELETE FROM shear_blanking_fts WHERE source_id=?", (rec["source_id"],))
        connection.execute(
            "INSERT INTO shear_blanking_fts VALUES (?,?,?,?,?)",
            (rec["source_id"], rec["title"], rec["authors"], rec["abstract"], rec["publisher"]),
        )
        written.append({"source_id": rec["source_id"], "sha256": digest})
    return written, quarantined


def write_calibration(connection: sqlite3.Connection) -> dict:
    connection.execute("DELETE FROM shear_blanking_calibration")
    now = datetime.now(timezone.utc).isoformat()
    for material, temper, model, parameter, value, unit, url, trace, usable in EXTRACTED_CALIBRATION:
        connection.execute(
            "INSERT INTO shear_blanking_calibration "
            "(material,temper,model,parameter,value,unit,source_id,source_url,"
            "traceability,usable_for_calibration,note,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (material, temper, model, parameter, value, unit, "url:" + url, url,
             trace, usable, CALIBRATION_NOTES[usable], now),
        )
    strength = connection.execute(
        "SELECT COUNT(*) FROM shear_blanking_calibration "
        "WHERE material='AA5052' AND usable_for_calibration=1 AND model='strength'"
    ).fetchone()[0]
    hardening = connection.execute(
        "SELECT COUNT(*) FROM shear_blanking_calibration "
        "WHERE material='AA5052' AND usable_for_calibration=1 AND model LIKE '%hardening%'"
    ).fetchone()[0]
    return {"rows": len(EXTRACTED_CALIBRATION), "target_material": "AA5052 (MR536)",
            "aa5052_usable_strength_params": strength,
            "aa5052_usable_hardening_params": hardening,
            "damage_calibration_available": False}


def verify_readback(connection: sqlite3.Connection, written: list[dict]) -> dict:
    """Re-read every row and recompute the digest. This is the mojibake gate."""
    mismatches, corrupted = [], []
    for item in written:
        row = connection.execute(
            "SELECT title, authors, abstract, doi, url, content_sha256 "
            "FROM shear_blanking_sources WHERE source_id=?", (item["source_id"],)
        ).fetchone()
        if row is None:
            mismatches.append(item["source_id"])
            continue
        try:
            for value in row[:5]:
                validate_text(value or "", item["source_id"])
        except MojibakeError as exc:
            corrupted.append(f"{item['source_id']}: {exc}")
            continue
        payload = json.dumps(
            {"abstract": row[2], "authors": row[1], "doi": row[3], "title": row[0], "url": row[4]},
            ensure_ascii=False, sort_keys=True,
        )
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != row[5]:
            mismatches.append(item["source_id"])
    replacement_rows = connection.execute(
        "SELECT COUNT(*) FROM shear_blanking_sources "
        "WHERE title LIKE '%'||char(65533)||'%' OR abstract LIKE '%'||char(65533)||'%'"
    ).fetchone()[0]
    return {"rows_verified": len(written), "sha256_mismatches": mismatches,
            "corrupted": corrupted, "replacement_character_rows": replacement_rows}


HARVESTERS = (
    ("openalex", harvest_openalex),
    ("crossref", harvest_crossref),
    ("europepmc", harvest_europepmc),
    ("arxiv", harvest_arxiv),
)


def run(db_path: Path, rows: int, pause: float) -> dict:
    records: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()

    def add(batch: list[dict]) -> None:
        for rec in batch:
            if rec["source_id"] not in seen and rec.get("title"):
                seen.add(rec["source_id"])
                records.append(rec)

    for category, queries in CATEGORIES.items():
        for query in queries:
            for name, func in HARVESTERS:
                try:
                    add(func(query, category, rows))
                except Exception as exc:
                    errors.append(f"{name}[{query}]: {type(exc).__name__}: {exc}")
                time.sleep(pause)

    for jp_query, category in (("せん断", "blanking_process"), ("打抜き", "blanking_process"),
                               ("精密せん断", "blanking_process")):
        try:
            add(harvest_jstage(jp_query, category, rows))
        except Exception as exc:
            errors.append(f"jstage[{jp_query}]: {type(exc).__name__}: {exc}")
        time.sleep(pause)

    for name, func in (("direct_docs", harvest_direct_docs), ("github", harvest_github)):
        try:
            add(func())
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    # universal_growth.db has a permanently resident concurrent writer
    # (scripts/north_star_domain_harvest.py), so a single busy_timeout is not enough.
    connection = sqlite3.connect(db_path, timeout=300)
    connection.execute("PRAGMA busy_timeout=300000")
    tokenizer = ensure_schema(connection)
    for attempt in range(5):
        try:
            written, quarantined = write_rows(connection, records)
            calibration = write_calibration(connection)
            connection.commit()
            break
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc) or attempt == 4:
                raise
            connection.rollback()
            errors.append(f"write attempt {attempt}: {exc}")
            time.sleep(20)
    verification = verify_readback(connection, written)

    quarantined_ids = {q["source_id"] for q in quarantined}
    by_provider: dict[str, int] = {}
    by_access: dict[str, int] = {}
    for rec in records:
        if rec["source_id"] in quarantined_ids:
            continue
        by_provider[rec["provider"]] = by_provider.get(rec["provider"], 0) + 1
        by_access[rec["access_class"]] = by_access.get(rec["access_class"], 0) + 1
    japanese = connection.execute(
        "SELECT COUNT(*) FROM shear_blanking_sources WHERE language='ja'").fetchone()[0]
    connection.close()

    passed = (not verification["sha256_mismatches"] and not verification["corrupted"]
              and verification["replacement_character_rows"] == 0)
    return {"database": str(db_path), "fts_tokenizer": tokenizer,
            "harvested": len(written), "quarantined": quarantined,
            "by_provider": by_provider, "by_access_class": by_access,
            "japanese_rows": japanese, "verification": verification,
            "calibration": calibration,
            "encoding_gate": "PASS" if passed else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--rows", type=int, default=10)
    parser.add_argument("--pause", type=float, default=0.7)
    args = parser.parse_args()
    report = run(args.db, args.rows, args.pause)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["encoding_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
