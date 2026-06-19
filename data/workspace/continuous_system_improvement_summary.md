# Continuous System Improvement Summary

Updated: 2026-06-19 19:54:33 JST

## Strengths
- Email watchdog is running: updated 0.5 minutes ago
- Continuous email ingest is active: stage=full_backfill age=0.6 minutes
- Auto repair patrol is recent: updated 56.6 minutes ago
- Idle maintenance is recent: updated 56.4 minutes ago
- Risk notification patrol is recent: updated 56.5 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=16
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=1.3 minutes
- Paperless ingest audit confirms recent documents are indexed: age=19692.9 minutes
- n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200
- Docker Desktop UI watchdog is active: stage=healthy age=0.7 minutes
- Claudian watchdog is active: stage=healthy age=3.0 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=6.7 minutes
- Email blacklist hub API is reachable: blacklist=130 candidates=120
- Email search API is reachable: emails=14884 tasks=6823
- Email extraction quality snapshot is recent: deadline_detection_rate=74.2% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=713.4 minutes
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=3

## Weaknesses
- [HIGH] Paperless RAG watchdog is stale: state=healthy ageMinutes=1.3
- [MEDIUM] Paperless review artifacts are stale or failed: state=stale ok=True
- [MEDIUM] Paperless ingest API is unavailable: url=http://host.docker.internal:8000 detail=HTTPConnectionPool(host='localhost', port=8000): Max retries exceeded with url: /api/documents/?page_size=1 (Caused by NewConnectionError("HTTPConnection(host='localhost', port=8000): Failed to establish a new connection: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。"))
- [MEDIUM] Deadline extraction rate is below target: rate=74.2%

## Actions
- run_email_quality_eval: rc=0 reason=Refresh Gmail extraction quality metrics
- refresh_paperless_ingest_token: rc=1 reason=Paperless ingest auth should mint a fresh token when 401/403 occurs
- run_paperless_rag_watchdog: rc=0 reason=Paperless watchdog should restart ingest after token refresh
