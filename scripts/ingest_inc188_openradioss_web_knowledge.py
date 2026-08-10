# -*- coding: utf-8 -*-
"""Ingest bounded, source-traceable INC-188 web knowledge without mojibake."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "workspace" / "universal_growth.db"
USER_AGENT = "Clawstack-CAE-Knowledge/1.0 (bounded metadata-first research)"

SOURCES = (
    {
        "id": "altair-fail-johnson-2025",
        "title": "Radioss /FAIL/JOHNSON",
        "url": "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/fail_johnson_starter_r.htm",
        "access": "direct_free",
        "license": "publicly accessible official documentation; copyright Altair",
        "lesson": "Nonlinear plastic-strain failure with linear damage accumulation. Parameters require material calibration; do not borrow another alloy's constants.",
    },
    {
        "id": "altair-fail-gene1-2025",
        "title": "Radioss /FAIL/GENE1",
        "url": "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/fail_gene1_starter_r.htm",
        "access": "direct_free",
        "license": "publicly accessible official documentation; copyright Altair",
        "lesson": "GENE1 combines active criteria through NCS; its Shear input is tensorial shear strain. Abrupt thresholds are not accumulated ductile damage calibration.",
    },
    {
        "id": "altair-ruptured-plate-2022",
        "title": "Radioss ruptured plate ductile failure example",
        "url": "https://2022.help.altair.com/2022/hwsolvers/rad/topics/solvers/rad/ruptured_plate_ductile_failure_model_example_r.htm",
        "access": "direct_free",
        "license": "publicly accessible official example; copyright Altair",
        "lesson": "Official ductile rupture examples compare accumulated damage models. Example constants validate implementation behavior, not AA1060 calibration.",
    },
    {
        "id": "altair-results-checking-2025",
        "title": "Radioss results checking",
        "url": "https://2025.help.altair.com/2025/hwsolvers/rad/topics/solvers/rad/faq_rad_results_checking_r.htm",
        "access": "direct_free",
        "license": "publicly accessible official documentation; copyright Altair",
        "lesson": "Energy balance, added mass and termination messages must be checked together; a process exit code or TSTOP alone is not physical completion.",
    },
    {
        "id": "doi-10.1115-1.1285909",
        "title": "Prediction of Ductile Fracture in Metal Blanking",
        "url": "https://doi.org/10.1115/1.1285909",
        "access": "paid_or_subscription",
        "license": "metadata only; full text not downloaded",
        "lesson": "High-relevance blanking fracture paper. Queue for authorized acquisition; metadata alone cannot supply AA1060 constants.",
    },
    {
        "id": "makeitfrom-1060-h18-2020",
        "title": "1060-H18 Aluminum",
        "url": "https://www.makeitfrom.com/material-properties/1060-H18-Aluminum",
        "publisher": "MakeItFrom.com",
        "access": "direct_free",
        "license": "publicly accessible secondary material-property summary; copyright MakeItFrom.com",
        "lesson": "Screening values are E=68 GPa, elongation=4%, shear strength=75 MPa, UTS=130 MPa, yield=110 MPa and density=2.7 g/cm3. These expose the current A=200 MPa card as untraceable for 1060-H18, but do not calibrate failure damage.",
    },
)


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def validate_utf8(text: str) -> bytes:
    """Fail closed on replacement characters and common UTF-8/CP932 corruption."""
    bad_markers = ("\ufffd", "縺", "繧", "譁", "蜈")
    if any(marker in text for marker in bad_markers):
        raise ValueError("mojibake marker detected")
    encoded = text.encode("utf-8", errors="strict")
    if encoded.decode("utf-8", errors="strict") != text:
        raise ValueError("UTF-8 round-trip mismatch")
    return encoded


def fetch_metadata(url: str) -> tuple[int, str, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2_000_000)
        status = int(response.status)
        final_url = response.geturl()
    text = raw.decode("utf-8", errors="strict")
    parser = _MetadataParser()
    parser.feed(text)
    validate_utf8(parser.title + parser.description)
    return status, final_url, parser.title.strip(), parser.description.strip()


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS inc188_web_knowledge (
            source_id TEXT PRIMARY KEY,
            accessed_at TEXT NOT NULL,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL,
            final_url TEXT NOT NULL,
            publisher TEXT NOT NULL,
            access_class TEXT NOT NULL,
            license_note TEXT NOT NULL,
            http_status INTEGER,
            remote_description TEXT NOT NULL,
            extracted_lesson TEXT NOT NULL,
            fact_or_inference TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            encoding TEXT NOT NULL,
            ingest_status TEXT NOT NULL
        )
        """
    )


def ingest(db_path: Path) -> dict[str, object]:
    connection = sqlite3.connect(db_path, timeout=60)
    connection.execute("PRAGMA busy_timeout=60000")
    ensure_schema(connection)
    rows = []
    for source in SOURCES:
        status, final_url, remote_title, description = None, source["url"], "", ""
        ingest_status = "metadata_only"
        if source["access"] == "direct_free":
            status, final_url, remote_title, description = fetch_metadata(source["url"])
            ingest_status = (
                "verified_official_metadata"
                if source["id"].startswith("altair")
                else "verified_public_metadata"
            )
        payload = json.dumps(
            {"title": source["title"], "remote_title": remote_title,
             "description": description, "lesson": source["lesson"]},
            ensure_ascii=False, sort_keys=True,
        )
        digest = hashlib.sha256(validate_utf8(payload)).hexdigest()
        values = (
            source["id"], datetime.now(timezone.utc).isoformat(), source["title"],
            source["url"], final_url, source.get("publisher") or (
                "Altair" if source["id"].startswith("altair") else "ASME"
            ),
            source["access"], source["license"], status, description, source["lesson"],
            "fact_and_labeled_recommendation", digest, "utf-8", ingest_status,
        )
        connection.execute(
            "INSERT OR REPLACE INTO inc188_web_knowledge VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values,
        )
        rows.append({"source_id": source["id"], "status": ingest_status, "sha256": digest})
    connection.commit()
    replacement_count = connection.execute(
        "SELECT COUNT(*) FROM inc188_web_knowledge WHERE remote_description LIKE '%' || char(65533) || '%'"
    ).fetchone()[0]
    connection.close()
    if replacement_count:
        raise ValueError(f"DB contains {replacement_count} replacement-character rows")
    return {"database": str(db_path), "rows": rows, "replacement_character_rows": replacement_count}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    print(json.dumps(ingest(args.db), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
