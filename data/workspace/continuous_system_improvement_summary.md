# Continuous System Improvement Summary

Updated: 2026-06-12 19:53:13 JST

## Strengths
- Email watchdog is running: updated 0.4 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.5 minutes
- Auto repair patrol is recent: updated 17.9 minutes ago
- Idle maintenance is recent: updated 73.3 minutes ago
- Risk notification patrol is recent: updated 73.3 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=16
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=2.3 minutes
- Paperless ingest audit confirms recent documents are indexed: age=9611.8 minutes
- n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.5 minutes
- Claudian watchdog is active: stage=healthy age=2.0 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=2.1 minutes
- Email blacklist hub API is reachable: blacklist=130 candidates=120
- Email search API is reachable: emails=14872 tasks=6813
- Email extraction quality snapshot is recent: deadline_detection_rate=75.7% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=135.1 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=3

## Weaknesses
- [HIGH] Paperless RAG watchdog is stale: state=healthy ageMinutes=0.3
- [MEDIUM] Paperless review artifacts are stale or failed: state=stale ok=True
- [MEDIUM] Paperless ingest API is unavailable: url=http://127.0.0.1:8000 detail=HTTP 404
- [MEDIUM] Deadline extraction rate is below target: rate=75.7%

## Actions
- run_email_quality_eval: rc=0 reason=Refresh Gmail extraction quality metrics
- refresh_paperless_ingest_token: rc=1 reason=Paperless ingest auth should mint a fresh token when 401/403 occurs
- run_paperless_rag_watchdog: rc=0 reason=Paperless watchdog should restart ingest after token refresh
