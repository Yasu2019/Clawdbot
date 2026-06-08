import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_JSON = ROOT / "data" / "workspace" / "apps" / "growth_dashboard" / "autonomous_improvements.json"
JST = timezone(timedelta(hours=9))

EXCLUDED_SUBJECT_PREFIXES = (
    "chore(cae): Auto-backup",
    "Auto-backup",
)


def run_git(args):
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def load_existing():
    if not DASHBOARD_JSON.exists():
        return []
    try:
        data = json.loads(DASHBOARD_JSON.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def commit_records():
    raw = run_git(
        [
            "log",
            "--since=2026-06-04",
            "--max-count=40",
            "--pretty=format:%H%x09%h%x09%aI%x09%s",
        ]
    )
    records = []
    for line in raw.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        full_sha, short_sha, timestamp, subject = parts
        if any(subject.startswith(prefix) for prefix in EXCLUDED_SUBJECT_PREFIXES):
            continue
        if "Autonomously integrated Cross-WLF" in subject:
            continue
        name_status = run_git(["show", "--name-status", "--format=", full_sha])
        stat = run_git(["show", "--stat", "--format=", "--stat-count=8", full_sha])
        records.append(
            {
                "timestamp": timestamp,
                "record_id": short_sha,
                "entry_type": "git_commit",
                "commit": short_sha,
                "challenge": subject,
                "know_how": "Recent AI implementation recorded from Git history.",
                "capability_comment": "Recent code change is now visible in the autonomous improvement dashboard.",
                "before_code": name_status or "(no changed files listed)",
                "after_code": stat or subject,
            }
        )
    return records


def merge_records(git_records, existing_records):
    seen_commits = set()
    merged = []
    for record in git_records:
        commit = record.get("commit") or record.get("record_id")
        if commit in seen_commits:
            continue
        seen_commits.add(commit)
        merged.append(record)

    for record in existing_records:
        commit = record.get("commit")
        if commit and commit in seen_commits:
            continue
        merged.append(record)

    def sort_key(record):
        timestamp = str(record.get("timestamp") or "")
        return timestamp

    merged.sort(key=sort_key, reverse=True)
    return merged[:80]


def main():
    existing = load_existing()
    git_records = commit_records()
    merged = merge_records(git_records, existing)
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] wrote {DASHBOARD_JSON}")
    print(f"[OK] git_records={len(git_records)} total_records={len(merged)}")


if __name__ == "__main__":
    main()
