# -*- coding: utf-8 -*-
"""
Moldflow 2010 の材料ファイルをローカル SQLite にカタログ化し、
必要なら Turso にも同期する。

対象:
  - C:\\Program Files\\Autodesk\\Moldflow Insight 2010\\data\\udb\\*.udb
  - C:\\Program Files\\Autodesk\\Moldflow Insight 2010\\data\\dat\\*.csv / *.udb

使い方:
  python scripts/import_moldflow_materials.py
  python scripts/import_moldflow_materials.py --sync-turso
  python scripts/import_moldflow_materials.py --sync-turso --limit 20
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import sqlite3
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_INSTALL_ROOT = pathlib.Path(r"C:\Program Files\Autodesk\Moldflow Insight 2010")
DEFAULT_DB = REPO_ROOT / "data" / "workspace" / "moldflow_materials.db"


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k and k not in os.environ:
            os.environ[k] = v.strip()


_load_env()

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
TURSO_PIPELINE_URL = TURSO_URL.rstrip("/") + "/v2/pipeline" if TURSO_URL else ""


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


@dataclass(frozen=True)
class MaterialFile:
    source_path: str
    relative_path: str
    file_name: str
    source_kind: str
    vendor: str
    version_tag: str
    extension: str
    size_bytes: int
    sha256: str
    modified_utc: str
    imported_utc: str


DDL = """
CREATE TABLE IF NOT EXISTS moldflow_material_files (
    source_path   TEXT PRIMARY KEY,
    relative_path TEXT NOT NULL,
    file_name     TEXT NOT NULL,
    source_kind   TEXT NOT NULL,
    vendor        TEXT NOT NULL,
    version_tag   TEXT NOT NULL,
    extension     TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    sha256        TEXT NOT NULL,
    modified_utc  TEXT NOT NULL,
    imported_utc  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_vendor
    ON moldflow_material_files(vendor);

CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_kind
    ON moldflow_material_files(source_kind);

CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_sha256
    ON moldflow_material_files(sha256);
"""

TURSO_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS moldflow_material_files (
        source_path   TEXT PRIMARY KEY,
        relative_path TEXT NOT NULL,
        file_name     TEXT NOT NULL,
        source_kind   TEXT NOT NULL,
        vendor        TEXT NOT NULL,
        version_tag   TEXT NOT NULL,
        extension     TEXT NOT NULL,
        size_bytes    INTEGER NOT NULL,
        sha256        TEXT NOT NULL,
        modified_utc  TEXT NOT NULL,
        imported_utc  TEXT NOT NULL
    )
    """.strip(),
    "CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_vendor ON moldflow_material_files(vendor)",
    "CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_kind ON moldflow_material_files(source_kind)",
    "CREATE INDEX IF NOT EXISTS idx_moldflow_material_files_sha256 ON moldflow_material_files(sha256)",
]


def parse_vendor_version(file_name: str) -> tuple[str, str]:
    stem = pathlib.Path(file_name).stem
    parts = stem.split(".")
    if len(parts) >= 2 and re.fullmatch(r"\d+", parts[-1]):
        vendor = ".".join(parts[:-1]) or stem
        version = parts[-1]
    else:
        vendor = stem
        version = ""
    vendor = vendor.replace("_", " ").strip() or "unknown"
    return vendor, version


def detect_source_kind(path: pathlib.Path, install_root: pathlib.Path) -> str:
    try:
        rel = path.relative_to(install_root)
    except Exception:
        return "external"
    parts = {p.lower() for p in rel.parts}
    if "udb" in parts:
        return "udb"
    if "dat" in parts:
        return "dat"
    return "other"


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_files(install_root: pathlib.Path, limit: int | None = None) -> list[pathlib.Path]:
    roots = [
        install_root / "data" / "udb",
        install_root / "data" / "dat",
    ]
    files: list[pathlib.Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.udb", "*.csv"):
            files.extend(sorted(root.glob(pattern)))
    files = [p for p in files if p.is_file()]
    files.sort(key=lambda p: str(p).lower())
    if limit is not None:
        return files[:limit]
    return files


def build_records(files: Iterable[pathlib.Path], install_root: pathlib.Path) -> list[MaterialFile]:
    now = datetime.now(timezone.utc).isoformat()
    records: list[MaterialFile] = []
    for path in files:
        stat = path.stat()
        vendor, version = parse_vendor_version(path.name)
        try:
            rel = path.relative_to(install_root)
            rel_str = str(rel)
        except Exception:
            rel_str = str(path)
        records.append(
            MaterialFile(
                source_path=str(path),
                relative_path=rel_str,
                file_name=path.name,
                source_kind=detect_source_kind(path, install_root),
                vendor=vendor,
                version_tag=version,
                extension=path.suffix.lstrip(".").lower(),
                size_bytes=stat.st_size,
                sha256=sha256_file(path),
                modified_utc=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                imported_utc=now,
            )
        )
    return records


def init_sqlite(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(DDL)
    con.commit()
    return con


def upsert_sqlite(con: sqlite3.Connection, records: list[MaterialFile]) -> int:
    sql = """
    INSERT INTO moldflow_material_files (
        source_path, relative_path, file_name, source_kind, vendor, version_tag,
        extension, size_bytes, sha256, modified_utc, imported_utc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source_path) DO UPDATE SET
        relative_path=excluded.relative_path,
        file_name=excluded.file_name,
        source_kind=excluded.source_kind,
        vendor=excluded.vendor,
        version_tag=excluded.version_tag,
        extension=excluded.extension,
        size_bytes=excluded.size_bytes,
        sha256=excluded.sha256,
        modified_utc=excluded.modified_utc,
        imported_utc=excluded.imported_utc
    """
    rows = [tuple(asdict(r).values()) for r in records]
    con.executemany(sql, rows)
    con.commit()
    return len(rows)


def turso_execute(requests_list: list[dict], dry_run: bool = False) -> bool:
    if dry_run:
        return True
    if not TURSO_URL or not TURSO_TOKEN:
        return False
    payload = json.dumps({"requests": requests_list}).encode("utf-8")
    req = urllib.request.Request(
        TURSO_PIPELINE_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())
        for r in body.get("results", []):
            if r.get("type") == "error":
                raise RuntimeError(r.get("error", {}).get("message", "turso error"))
    return True


def sync_turso(records: list[MaterialFile], dry_run: bool = False) -> str:
    if not TURSO_URL or not TURSO_TOKEN:
        return "skip_no_turso_credentials"
    if not records:
        return "skip_empty"
    try:
        requests_list = [{"type": "execute", "stmt": {"sql": stmt}} for stmt in TURSO_DDL_STATEMENTS]
        for r in records:
            requests_list.append({
                "type": "execute",
                "stmt": {
                    "sql": """
                    INSERT INTO moldflow_material_files (
                        source_path, relative_path, file_name, source_kind, vendor, version_tag,
                        extension, size_bytes, sha256, modified_utc, imported_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_path) DO UPDATE SET
                        relative_path=excluded.relative_path,
                        file_name=excluded.file_name,
                        source_kind=excluded.source_kind,
                        vendor=excluded.vendor,
                        version_tag=excluded.version_tag,
                        extension=excluded.extension,
                        size_bytes=excluded.size_bytes,
                        sha256=excluded.sha256,
                        modified_utc=excluded.modified_utc,
                        imported_utc=excluded.imported_utc
                    """.strip(),
                    "args": [
                        {"type": "text", "value": r.source_path},
                        {"type": "text", "value": r.relative_path},
                        {"type": "text", "value": r.file_name},
                        {"type": "text", "value": r.source_kind},
                        {"type": "text", "value": r.vendor},
                        {"type": "text", "value": r.version_tag},
                        {"type": "text", "value": r.extension},
                        {"type": "integer", "value": str(r.size_bytes)},
                        {"type": "text", "value": r.sha256},
                        {"type": "text", "value": r.modified_utc},
                        {"type": "text", "value": r.imported_utc},
                    ],
                },
            })
        requests_list.append({"type": "close"})
        turso_execute(requests_list, dry_run=dry_run)
        return "ok"
    except Exception as exc:
        return f"error:{exc}"[:200]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install-root", default=str(DEFAULT_INSTALL_ROOT))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sync-turso", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    install_root = pathlib.Path(args.install_root)
    db_path = pathlib.Path(args.db)
    if not install_root.exists():
        raise SystemExit(f"install root not found: {install_root}")

    files = scan_files(install_root, limit=args.limit)
    log(f"scan_count={len(files)} install_root={install_root}")
    records = build_records(files, install_root)

    if args.dry_run:
        for r in records[:10]:
            log(f"dry_run {r.source_kind} {r.vendor} {r.file_name} sha256={r.sha256[:12]}")
        if len(records) > 10:
            log(f"dry_run truncated={len(records) - 10}")
        return 0

    con = init_sqlite(db_path)
    inserted = upsert_sqlite(con, records)
    con.close()
    log(f"sqlite_ok db={db_path} rows={inserted}")

    if args.sync_turso:
        status = sync_turso(records)
        log(f"turso={status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
