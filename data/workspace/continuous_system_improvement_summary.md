# Continuous System Improvement Summary

Updated: 2026-04-26 12:32:45 JST

## Strengths
- Email watchdog is running: updated 1.3 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.8 minutes
- Risk notification patrol is recent: updated 169.3 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=13
- Paperless RAG watchdog is active: updated 0.9 minutes ago
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=1.4 minutes
- Paperless review artifacts are recent: age=0.9 minutes reason=ingest_progress
- Paperless ingest audit confirms recent documents are indexed: age=2.9 minutes
- Paperless ingest API authentication is valid: url=http://127.0.0.1:8000 status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.9 minutes
- Claudian watchdog is active: stage=healthy age=1.1 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=6.0 minutes
- Email extraction quality snapshot is recent: deadline_detection_rate=82.2% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=95.5 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=4
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [MEDIUM] Auto repair patrol is stale: state=stale ageMinutes=127.2
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=22683.7
- [HIGH] Email blacklist hub API is offline or stale: processAlive=True state=healthy ageMinutes=127.7 configOk=False candidatesOk=False
- [HIGH] Email search API is offline: processAlive=True apiOk=False

## Actions
- start_email_blacklist_hub: rc=0 reason=Email blacklist hub API is offline or stale
- start_email_search_api: rc=0 reason=Email search API is offline
- run_auto_repair: rc=None reason=Auto repair should re-evaluate email-related health
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
