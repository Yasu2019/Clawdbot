# Quality Incident Report: Autonomous Improvements Not Updating

Date: 2026-06-09 JST

## Issue

The Growth Dashboard section "Autonomous Code Improvements" did not show recent AI implementation work, even though several code changes had been made and pushed.

## Impact

The dashboard made it look as if collected knowledge was not producing code improvements. This reduced traceability from research/source collection to actual implementation work.

## 5 Whys

1. Why did the dashboard not show recent improvements?
   Recent implementation commits were not written into `autonomous_improvements.json`.

2. Why were they not written?
   Only `scripts/autonomous_coder.py` writes that JSON, and it is a specialized Moldflow/Cross-WLF self-improvement flow.

3. Why did normal AI coding work not appear?
   The dashboard had no bridge from Git commit history to the autonomous improvement feed.

4. Why was this missed?
   The source collection dashboard and the code improvement dashboard used separate data sources without a freshness check.

5. Why did it create user concern about information quality?
   The UI wording implied that useful gathered knowledge should appear as code improvements, but the implementation only recorded one narrow automation path.

## Root Cause

The dashboard data model was too narrow. It treated only `autonomous_coder.py` outputs as autonomous improvements and ignored normal AI implementation commits.

## Countermeasures

1. Added `scripts/export_autonomous_improvements_from_git.py`.
2. The script reads recent Git commits since 2026-06-04 and converts implementation commits into dashboard entries.
3. Existing `autonomous_coder.py` records are preserved and merged.
4. Backup and auto-backup commits are filtered out.
5. The generated dashboard JSON now contains both recent Git-based improvements and legacy autonomous-coder entries.

## Verification

- `python -m py_compile scripts\export_autonomous_improvements_from_git.py`
- `python scripts\export_autonomous_improvements_from_git.py`
- Result: `git_records=16 total_records=20`

## Prevention Rule

When a dashboard claims to show AI improvement history, it must have at least one exporter that reflects the normal implementation path, not only a narrow experimental automation path.
