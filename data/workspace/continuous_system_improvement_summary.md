# Continuous System Improvement Summary

Updated: 2026-04-24 14:39:37 JST

## Strengths
- Email watchdog is running: updated 1.4 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.5 minutes
- Auto repair patrol is recent: updated 41.7 minutes ago
- Risk notification patrol is recent: updated 52.4 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=13
- Paperless RAG watchdog is active: updated 0.9 minutes ago
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=1.3 minutes
- Paperless review artifacts are recent: age=0.9 minutes reason=ingest_progress
- Paperless ingest audit confirms recent documents are indexed: age=0.6 minutes
- Paperless ingest API authentication is valid: url=http://127.0.0.1:8000 status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.6 minutes
- Claudian watchdog is active: stage=healthy age=0.7 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=2.7 minutes
- Email blacklist hub API is reachable: blacklist=323 candidates=120
- Email search API is reachable: emails=42040 tasks=22059
- Email extraction quality snapshot is recent: deadline_detection_rate=81.5% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=262.3 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=4
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=19940.6

## Actions
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
