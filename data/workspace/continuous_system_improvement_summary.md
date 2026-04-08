# Continuous System Improvement Summary

Updated: 2026-04-09 05:52:21 JST

## Strengths
- Email watchdog is running: updated 0.9 minutes ago
- Auto repair patrol is recent: updated 21.0 minutes ago
- Risk notification patrol is recent: updated 10.4 minutes ago
- Paperless RAG watchdog is active: updated 0.2 minutes ago
- Paperless ingest heartbeat is fresh: stage=idle age=2.1 minutes
- Paperless review artifacts are recent: age=2.9 minutes reason=ingest_progress
- Email safety policy is present: draft_only=true auto_send=false
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [HIGH] Continuous email ingest is unhealthy: stage=error state=healthy ageMinutes=0.4
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=153.0
- [HIGH] Learning engine health endpoint is offline: all configured health URLs failed; lastRepairResult=skipped_in_headless_native_mode repairAgeMinutes=10.2
- [HIGH] Paperless ingest audit found lag or is stale: state=stale status=healthy recentMissing=0
- [MEDIUM] Docker Desktop UI watchdog is stale or missing: state=missing stage=unknown ageMinutes=None
- [MEDIUM] Email extraction quality snapshot is missing or stale: state=healthy ageMinutes=10.2
- [HIGH] Email SQLite integrity check failed or is stale: state=healthy ok=False

## Actions
- start_docker_desktop_ui_watchdog: rc=0 reason=Docker Desktop UI watchdog is missing or stale
- run_auto_repair: rc=0 reason=Auto repair should re-evaluate email-related health
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
- run_risk_notification: rc=0 reason=Push current risks through notification patrol
- run_learning_engine_repair: rc=0 reason=Recover learning_engine and Docker path if 8110 is offline
- run_email_quality_eval: rc=1 reason=Refresh Gmail extraction quality metrics
- run_email_integrity_check: rc=0 reason=Refresh SQLite integrity status and catch corruption early
