from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
HOST_CSV = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCS = ROOT / "iatf_system" / "db" / "documents"
DEV_DOCS = ROOT / "data" / "state" / "IATF_documents"
STATUS_PATH = ROOT / "data" / "workspace" / "iatf_seed_auto_update_status.json"
JQA_ROOT = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "審査報告書"
MANUFACTURING_ROOT = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "製造工程設計"
TARGETS = [
    {"container": "iatf_system_dev-web-1", "environment": "development"},
    {"container": "iatf_system-web-1", "environment": "production"},
]
BACKUP_DIR = ROOT / "backups" / "iatf_seed_auto_update"

STAGE_BY_KIND = {
    "設計計画書": "105",
    "設計検証チェックリスト": "106",
    "Ｄ.R会議議事録": "112",
    "D.R会議議事録": "112",
}


@dataclass
class Candidate:
    source_type: str
    filename: str
    bytes_data: bytes
    source_path: str
    metadata: dict[str, str]

    @property
    def size(self) -> int:
        return len(self.bytes_data)

    @property
    def sha1(self) -> str:
        return hashlib.sha1(self.bytes_data).hexdigest()


def load_attachedfile_rows() -> list[dict[str, str]]:
    if not HOST_CSV.exists():
        return []
    with HOST_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def attachedfile_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    indexed: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        filename = (row.get("filename") or "").strip()
        if not filename:
            continue
        indexed.setdefault(filename, []).append(row)
    return indexed


def next_document_number(existing_rows: list[dict[str, str]], year: int) -> str:
    max_sequence = 0
    for row in existing_rows:
        value = row.get("documentnumber") or ""
        match = re.fullmatch(rf"{year}-JQA-(\d{{3}})", value)
        if match:
            max_sequence = max(max_sequence, int(match.group(1)))
    return f"{year}-JQA-{max_sequence + 1:03d}"


def jqa_candidates(existing_rows: list[dict[str, str]]) -> list[Candidate]:
    candidates: list[Candidate] = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for path in sorted(JQA_ROOT.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            bytes_data = path.read_bytes()
            year_match = re.search(r"(20\d{2})", path.name)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            metadata = {
                "filename": path.name,
                "category": "2",
                "partnumber": "",
                "materialcode": "",
                "phase": "",
                "stage": "",
                "description": "JQA審査報告書 auto sync",
                "status": "完了",
                "documenttype": "pdf",
                "documentname": Path(path.name).stem,
                "documentrev": "",
                "documentcategory": "JQA審査報告書",
                "documentnumber": next_document_number(existing_rows, year),
                "start_time": now_text,
                "deadline_at": now_text,
                "end_at": now_text,
                "goal_attainment_level": "100",
                "tasseido": "100",
                "object": "object1",
            }
            candidates.append(Candidate("jqa_report", path.name, bytes_data, str(path), metadata))
        elif suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    member_name = Path(info.filename).name
                    if Path(member_name).suffix.lower() != ".pdf":
                        continue
                    bytes_data = zf.read(info)
                    year_match = re.search(r"(20\d{2})", member_name)
                    year = int(year_match.group(1)) if year_match else datetime.now().year
                    metadata = {
                        "filename": member_name,
                        "category": "2",
                        "partnumber": "",
                        "materialcode": "",
                        "phase": "",
                        "stage": "",
                        "description": "JQA審査報告書 auto sync",
                        "status": "完了",
                        "documenttype": "pdf",
                        "documentname": Path(member_name).stem,
                        "documentrev": "",
                        "documentcategory": "JQA審査報告書",
                        "documentnumber": next_document_number(existing_rows, year),
                        "start_time": now_text,
                        "deadline_at": now_text,
                        "end_at": now_text,
                        "goal_attainment_level": "100",
                        "tasseido": "100",
                        "object": "object1",
                    }
                    candidates.append(
                        Candidate("jqa_report", member_name, bytes_data, f"{path}::{info.filename}", metadata)
                    )
    return candidates


def normalize_doc_kind(name: str) -> str | None:
    for kind in STAGE_BY_KIND:
        if kind in name:
            return kind
    return None


def parse_partnumber(name: str) -> str:
    match = re.search(r"(NT\d+-P\d+(?:-\d+)?)", name)
    return match.group(1) if match else ""


def parse_materialcode(name: str) -> str:
    match = re.search(r"_(PM[0-9A-Z]+)(?:_|【|\.|$)", name)
    return match.group(1) if match else ""


def manufacturing_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for zip_path in sorted(MANUFACTURING_ROOT.glob("*.zip")):
        seen: set[str] = set()
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                filename = Path(info.filename).name
                if filename in seen:
                    continue
                kind = normalize_doc_kind(filename)
                if not kind:
                    continue
                seen.add(filename)
                candidates.append(
                    Candidate(
                        "manufacturing_design",
                        filename,
                        zf.read(info),
                        f"{zip_path}::{info.filename}",
                        {
                            "filename": filename,
                            "category": "1",
                            "partnumber": parse_partnumber(filename),
                            "materialcode": parse_materialcode(filename),
                            "phase": "10",
                            "stage": STAGE_BY_KIND[kind],
                            "description": "",
                            "status": "完了",
                            "documenttype": "",
                            "documentname": Path(filename).stem.lstrip("_"),
                            "documentrev": "",
                            "documentcategory": "",
                            "documentnumber": "",
                            "start_time": now_text,
                            "deadline_at": now_text,
                            "end_at": now_text,
                            "goal_attainment_level": "100",
                            "tasseido": "100",
                            "object": "object1",
                        },
                    )
                )
    return candidates


def classify(candidates: list[Candidate], csv_index: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {
        "new": [],
        "missing_csv_only": [],
        "changed_existing": [],
        "missing_document_only": [],
        "unchanged": [],
    }
    for candidate in candidates:
        doc_path = HOST_DOCS / candidate.filename
        existing_rows = csv_index.get(candidate.filename, [])
        doc_exists = doc_path.exists()
        doc_size = doc_path.stat().st_size if doc_exists else None
        payload = {
            "source_type": candidate.source_type,
            "filename": candidate.filename,
            "source_path": candidate.source_path,
            "source_size": candidate.size,
            "host_document_exists": doc_exists,
            "host_document_size": doc_size,
            "metadata": candidate.metadata,
        }
        if not existing_rows and doc_exists:
            result["missing_csv_only"].append(payload)
        elif not existing_rows:
            result["new"].append(payload)
        elif not doc_exists:
            result["missing_document_only"].append(payload)
        elif doc_size != candidate.size:
            result["changed_existing"].append(payload)
        else:
            result["unchanged"].append(payload)
    return result


def backup_attachedfile() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if HOST_CSV.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(HOST_CSV, BACKUP_DIR / f"attachedfile_{stamp}.csv")


def append_csv_rows(rows: list[dict[str, str]]) -> None:
    backup_attachedfile()
    headers = [
        "filename", "category", "partnumber", "materialcode", "phase", "stage", "description", "status",
        "documenttype", "documentname", "documentrev", "documentcategory", "documentnumber",
        "start_time", "deadline_at", "end_at", "goal_attainment_level", "tasseido", "object",
    ]
    existing_keys = set()
    if HOST_CSV.exists():
        with HOST_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                existing_keys.add((row.get("filename", ""), row.get("category", ""), row.get("stage", "")))
    else:
        HOST_CSV.parent.mkdir(parents=True, exist_ok=True)
        with HOST_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
            csv.DictWriter(handle, fieldnames=headers).writeheader()

    with HOST_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        for row in rows:
            key = (row.get("filename", ""), row.get("category", ""), row.get("stage", ""))
            if key in existing_keys:
                continue
            writer.writerow({header: row.get(header, "") for header in headers})
            existing_keys.add(key)


def write_documents(candidates: list[Candidate]) -> list[str]:
    HOST_DOCS.mkdir(parents=True, exist_ok=True)
    DEV_DOCS.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for candidate in candidates:
        for target_dir in (HOST_DOCS, DEV_DOCS):
            (target_dir / candidate.filename).write_bytes(candidate.bytes_data)
        written.append(candidate.filename)
    return written


def run_attachedfile_seed_import(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    payload_b64 = base64.b64encode(json.dumps(rows, ensure_ascii=False).encode("utf-8")).decode("ascii")
    runner = f"""
# encoding: UTF-8
require "json"
require "base64"
rows = JSON.parse(Base64.decode64("{payload_b64}"))
puts JSON.generate(AttachedfileSeedImportService.call(rows: rows))
"""
    results = []
    for target in TARGETS:
        completed = subprocess.run(
            [
                "docker", "exec", "-i", target["container"],
                "bundle", "exec", "rails", "runner", "-e", target["environment"], "-"
            ],
            input=runner.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        results.append(
            {
                "container": target["container"],
                "environment": target["environment"],
                "returncode": completed.returncode,
                "stdout": completed.stdout.decode("utf-8", errors="replace").strip(),
                "stderr": completed.stderr.decode("utf-8", errors="replace").strip(),
            }
        )
    return results


def run_jqa_ingest(candidates: list[Candidate]) -> list[dict[str, object]]:
    payload = [
        {
            "filename": candidate.filename,
            "base64": base64.b64encode(candidate.bytes_data).decode("ascii"),
        }
        for candidate in candidates
    ]
    payload_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    runner = f"""
# encoding: UTF-8
require "json"
require "base64"

class UploadedStub
  attr_reader :original_filename
  def initialize(original_filename, bytes)
    @original_filename = original_filename
    @bytes = bytes
  end
  def read
    @bytes
  end
  def rewind; end
end

payload = JSON.parse(Base64.decode64("{payload_b64}"))
files = payload.map {{ |item| UploadedStub.new(item.fetch("filename"), Base64.decode64(item.fetch("base64"))) }}
puts JSON.generate(JqaAuditReportIngestService.call(files: files, description: "JQA report auto sync"))
"""
    results = []
    for target in TARGETS:
        completed = subprocess.run(
            [
                "docker", "exec", "-i", target["container"],
                "bundle", "exec", "rails", "runner", "-e", target["environment"], "-"
            ],
            input=runner.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        results.append(
            {
                "container": target["container"],
                "environment": target["environment"],
                "returncode": completed.returncode,
                "stdout": completed.stdout.decode("utf-8", errors="replace").strip(),
                "stderr": completed.stderr.decode("utf-8", errors="replace").strip(),
            }
        )
    return results


def build_status(mode: str, classification: dict[str, list[dict[str, object]]], apply_result: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": mode,
        "summary": {key: len(value) for key, value in classification.items()},
        "new_items": classification["new"],
        "missing_csv_only": classification["missing_csv_only"],
        "changed_existing": classification["changed_existing"],
        "missing_document_only": classification["missing_document_only"],
        "apply_result": apply_result or {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto diff updater for IATF seed assets")
    parser.add_argument("--apply", action="store_true", help="Apply low-risk updates")
    args = parser.parse_args()

    existing_rows = load_attachedfile_rows()
    index = attachedfile_index(existing_rows)
    candidates = jqa_candidates(existing_rows) + manufacturing_candidates()
    classification = classify(candidates, index)

    apply_result: dict[str, object] | None = None
    if args.apply and (classification["new"] or classification["missing_csv_only"] or classification["missing_document_only"]):
        filename_map = {candidate.filename: candidate for candidate in candidates}
        write_only_candidates = [
            filename_map[item["filename"]]
            for item in classification["missing_csv_only"]
            if item["filename"] in filename_map
        ]
        import_candidates = [
            filename_map[item["filename"]]
            for item in classification["new"] + classification["missing_document_only"]
            if item["filename"] in filename_map
        ]
        jqa_apply = [c for c in import_candidates if c.source_type == "jqa_report"]
        generic_apply = [c for c in import_candidates if c.source_type != "jqa_report"]

        written = write_documents(import_candidates) if import_candidates else []
        if write_only_candidates or jqa_apply or generic_apply:
            append_csv_rows([item.metadata for item in write_only_candidates + jqa_apply + generic_apply])
        jqa_results = run_jqa_ingest(jqa_apply) if jqa_apply else []
        generic_results = run_attachedfile_seed_import([item.metadata for item in generic_apply]) if generic_apply else []

        apply_result = {
            "written_documents_count": len(written),
            "write_only_count": len(write_only_candidates),
            "jqa_import_count": len(jqa_apply),
            "generic_import_count": len(generic_apply),
            "jqa_results": jqa_results,
            "generic_results": generic_results,
        }
        append_history_entry(
            {
                "type": "auto_diff_sync",
                "title": "IATF seed auto diff sync applied",
                "source": "審査報告書 / 製造工程設計",
                "record_count": len(apply_candidates),
                "details": {
                    "new_count": len(classification["new"]),
                    "missing_csv_only_count": len(classification["missing_csv_only"]),
                    "missing_document_only_count": len(classification["missing_document_only"]),
                    "changed_existing_count": len(classification["changed_existing"]),
                    "applied_filenames": [item.filename for item in write_only_candidates + import_candidates],
                },
            }
        )

    status = build_status("apply" if args.apply else "dry_run", classification, apply_result)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
