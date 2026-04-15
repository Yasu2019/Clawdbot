# Continuous System Improvement Summary

Updated: 2026-04-15 21:46:12 JST

## Strengths
- Email watchdog is running: updated 1.3 minutes ago
- Continuous email ingest is active: stage=idle age=3.8 minutes
- Auto repair patrol is recent: updated 84.3 minutes ago
- Risk notification patrol is recent: updated 147.8 minutes ago
- Learning engine health endpoint is reachable: url=http://localhost:8110/health collections=10
- Gateway ingest watchdog process count is healthy: processes=1
- Paperless ingest heartbeat is fresh: stage=idle age=2.3 minutes
- Paperless ingest audit confirms recent documents are indexed: age=4258.8 minutes
- Docker Desktop UI watchdog is active: stage=healthy age=0.7 minutes
- Email blacklist hub API is reachable: blacklist=323 candidates=3
- Email search API is reachable: emails=23511 tasks=9410
- Email extraction quality snapshot is recent: deadline_detection_rate=82.0% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Outbound delivery allowlist guard is enforced: gmail=y.suzuki.hk@gmail.com telegram=8173025084 blocked=0
- Email SQLite integrity check is recent: age=179.6 minutes
- Historical Gmail backfill still targets January 2026 onward: last range 2026-01-01..2026-04-14
- Gmail filter telemetry is visible in ingest summaries: skipped_by_filter=2
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=7407.2
- [HIGH] Paperless RAG watchdog is stale: state=healthy ageMinutes=0.9
- [MEDIUM] Paperless review artifacts are stale or failed: state=stale ok=True
- [MEDIUM] Paperless ingest API is unavailable: url=http://host.docker.internal:8000 detail=('Connection aborted.', ConnectionResetError(10054, '既存の接続はリモート ホストに強制的に切断されました。', None, 10054, None))
- [MEDIUM] Claudian watchdog is stale or missing: state=stale stage=warning ageMinutes=3813.5
- [MEDIUM] Mini PC optimizer watchdog is stale or missing: state=stale stage=healthy ageMinutes=3816.8

## Actions
- start_claudian_watchdog: rc=0 reason=Claudian watchdog is missing or stale
- start_minipc_optimizer_watchdog: rc=0 reason=Mini PC optimizer watchdog is missing or stale
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
- refresh_paperless_ingest_token: rc=1 reason=Paperless ingest auth should mint a fresh token when 401/403 occurs
- run_paperless_rag_watchdog: rc=0 reason=Paperless watchdog should restart ingest after token refresh
