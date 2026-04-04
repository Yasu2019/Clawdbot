# Continuous System Improvement Summary

Updated: 2026-04-04 11:33:28 JST

## Strengths
- Email watchdog is running: updated 1.0 minutes ago
- Continuous email ingest is active: stage=idle age=4.1 minutes
- Auto repair patrol is recent: updated 94.9 minutes ago
- Risk notification patrol is recent: updated 1.5 minutes ago
- Paperless ingest heartbeat is fresh: stage=polling age=0.4 minutes
- Paperless review artifacts are recent: age=154.2 minutes reason=ingest_progress
- Email extraction quality snapshot is recent: deadline_detection_rate=80.5% reply_detail_detection_rate=100.0%
- Email safety policy is present: draft_only=true auto_send=false
- Email SQLite integrity check is recent: age=303.4 minutes
- Improvement readiness checks are all passing: 3/3 checks passed

## Weaknesses
- [MEDIUM] Idle maintenance is stale: state=stale ageMinutes=1771.7
- [HIGH] Learning engine health endpoint is offline: all configured health URLs failed; lastRepairResult=skipped_in_headless_native_mode repairAgeMinutes=10.2
- [HIGH] Paperless RAG watchdog is stale: state=stale ageMinutes=154.2

## Actions
- run_idle_maintenance: rc=0 reason=Refresh maintenance cadence and status
- run_risk_notification: rc=0 reason=Push current risks through notification patrol
- run_learning_engine_repair: rc=0 reason=Recover learning_engine and Docker path if 8110 is offline
