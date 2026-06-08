# Quality Incident Report: IATF YouTube Dashboard Looked Stale

Date: 2026-06-09 JST

## Issue

The Growth Dashboard "YouTube IATF Analysis" section did not visibly progress even though the YouTube monitor had processed many videos.

## Impact

The user could not tell whether IATF video analysis was active, how many videos were indexed, how many were analyzed, or which videos were blocked by missing transcripts.

## 5 Whys

1. Why did the dashboard look stale?
   It displayed only a fixed representative table and no progress metrics.

2. Why were progress metrics missing?
   `iatf_youtube_summary.json` used an old list-only format limited to 20 rows.

3. Why did the old format persist?
   `export_knowledge_history.py` could overwrite the YouTube summary using an outdated exporter path.

4. Why was the current monitor state not visible?
   The dashboard did not reconcile the YouTube channel index, processed IDs, and DB summaries.

5. Why did this lead to confusion?
   The UI wording said representative processed data, but did not show indexed count, analyzed count, failed summaries, or missing transcript cases.

## Root Cause

The dashboard export was not designed as a progress report. It only exposed a small sample table and did not preserve operational status.

## Countermeasures

1. Rebuilt `scripts/export_iatf_dashboard.py` to export a v2 JSON object with progress counts and up to 80 recent rows.
2. Updated `scripts/export_knowledge_history.py` so it delegates YouTube summary generation to the new exporter instead of overwriting it with the legacy format.
3. Updated the Growth Dashboard to show indexed/analyzed/processed/failed/missing summary counts.
4. Refreshed `iatf_auditing_youtube_index.json` from YouTube: 349 indexed videos.
5. Verified the 3 missing summaries are transcript availability cases, not simply idle processing.

## Verification

- `python -m py_compile scripts\export_iatf_dashboard.py scripts\export_knowledge_history.py`
- `python scripts\update_iatf_auditing_youtube_index.py` -> `videos=349 total=349`
- `python scripts\export_iatf_dashboard.py` -> `items=80 analyzed=346 indexed=349 failed=28`
- Dashboard HTTP checks returned 200 for both page and JSON.

## Prevention Rule

Any dashboard section that represents a recurring data pipeline must show freshness and progress metrics, not only sample rows.
