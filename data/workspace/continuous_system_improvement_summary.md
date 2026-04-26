# Continuous System Improvement Summary

Updated: 2026-04-26 10:15:29 JST

## Strengths
- Email watchdog is running: updated 1.0 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.4 minutes
- Risk notification patrol is recent: updated 41.8 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=13
- Paperless RAG watchdog is active: updated 1.8 minutes ago
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=1.2 minutes
- Paperless review artifacts are recent: age=1.8 minutes reason=ingest_progress
- Paperless ingest audit confirms recent documents are indexed: age=1.5 minutes
- Paperless ingest API authentication is valid: url=http://127.0.0.1:8000 status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.7 minutes
- Claudian watchdog is active: stage=healthy age=2.7 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=9.4 minutes
- Email blacklist hub API is reachable: blacklist=323 candidates=120
- Email search API is reachable: emails=42061 tasks=22068
- Email extraction quality snapshot is recent: deadline_detection_rate=82.3% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=697.3 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=5
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [MEDIUM] Auto repair patrol is stale: state=stale ageMinutes=125.8
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=22556.2

## Actions
- run_auto_repair: rc=0 reason=Auto repair should re-evaluate email-related health
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
