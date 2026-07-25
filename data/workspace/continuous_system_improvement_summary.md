# Continuous System Improvement Summary

Updated: 2026-07-14 21:50:26 JST

## Strengths
- Email watchdog is running: updated 1.6 minutes ago
- Continuous email ingest is active: stage=idle age=1.8 minutes
- Auto repair patrol is recent: updated 57.8 minutes ago
- Idle maintenance is recent: updated 51.7 minutes ago
- Risk notification patrol is recent: updated 9.7 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=16
- Gateway ingest watchdog process count is healthy: processes=0
- Paperless ingest audit confirms recent documents are indexed: age=55808.3 minutes
- n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200
- Docker Desktop UI watchdog is active: stage=healthy age=1.5 minutes
- Claudian watchdog is active: stage=warning age=1.0 minutes
- Mini PC optimizer watchdog is active: stage=healthy age=2.8 minutes
- Email blacklist hub API is reachable: blacklist=130 candidates=120
- Email search API is reachable: emails=14928 tasks=6849
- Email extraction quality snapshot is recent: deadline_detection_rate=84.1% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=75.2 minutes

## Weaknesses
- [HIGH] Paperless RAG watchdog is stale: state=healthy ageMinutes=1.7
- [HIGH] Paperless ingest heartbeat is unhealthy: stage=idle state=stale ageMinutes=12615.1
- [MEDIUM] Paperless review artifacts are stale or failed: state=stale ok=True
- [MEDIUM] Paperless ingest API is unavailable: url=http://host.docker.internal:8000 detail=('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 10054, None))
- [MEDIUM] Gmail filter telemetry is missing from ingest summaries: Expected skipped_by_filter in recent Gmail summary so blacklist effectiveness stays observable

## Actions
- refresh_paperless_ingest_token: rc=1 reason=Paperless ingest auth should mint a fresh token when 401/403 occurs
- run_paperless_rag_watchdog: rc=0 reason=Paperless watchdog should restart ingest after token refresh
