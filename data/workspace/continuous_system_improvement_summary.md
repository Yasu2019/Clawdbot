# Continuous System Improvement Summary

Updated: 2026-06-03 22:30:39 JST

## Strengths
- Email watchdog is running: updated 0.7 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.6 minutes
- Auto repair patrol is recent: updated 27.3 minutes ago
- Idle maintenance is recent: updated 55.9 minutes ago
- Risk notification patrol is recent: updated 55.9 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=16
- Paperless RAG watchdog is active: updated 1.0 minutes ago
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=0.5 minutes
- Paperless review artifacts are recent: age=1.0 minutes reason=ingest_progress
- Paperless ingest audit confirms recent documents are indexed: age=0.6 minutes
- Paperless ingest API authentication is valid: url=http://127.0.0.1:8000 status=200
- n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.7 minutes
- Claudian watchdog is active: stage=warning age=3.0 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=6.0 minutes
- Email blacklist hub API is reachable: blacklist=130 candidates=120
- Email search API is reachable: emails=8028 tasks=4838
- Email extraction quality snapshot is recent: deadline_detection_rate=75.0% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=329.9 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=4

## Weaknesses
- [MEDIUM] Deadline extraction rate is below target: rate=75.0%

## Actions
- run_email_quality_eval: rc=0 reason=Refresh Gmail extraction quality metrics
