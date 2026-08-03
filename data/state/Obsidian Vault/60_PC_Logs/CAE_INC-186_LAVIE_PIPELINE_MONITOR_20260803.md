---
tags: [CAE, OpenFOAM, Moldflow, monitoring, RCA]
incident: INC-186
trouble_id: T083
bd_key: Clawdbot_Docker_20260125-270e
updated: 2026-08-03
---

# INC-186 LAVIE minus-X pipeline monitor gap

## Summary

NG: r35 completed at 11:09 JST but no dedicated process monitored transition to thermo fill. OK target: a 30 s heartbeat identifies the exact campaign phase. Impact was delay only; results remained intact.

## QC control plan

| Control | Method | Frequency | NG action |
|---|---|---|---|
| Monitor liveness | PID plus lock | 30 s | mark NG; restart one instance |
| Status freshness | `updated_at` age | 30 s | prohibit monitoring claim |
| Phase correctness | r35 status and cooling provenance | each cycle | fail closed |
| Accuracy label | exact `PROXY_GAP` | each cycle | reject artifact |

## FMEA

| Failure mode | Effect | Cause | Countermeasure |
|---|---|---|---|
| One-shot waiter exits | pipeline stalls | no state machine | persistent bounded monitor |
| General activity mistaken for progress | false report | status domains mixed | campaign phase field |
| Obsolete 35 s run restarts | waste/wrong physics | stale waiter reused | forbidden flag |
| Duplicate monitor | conflicting status | no lock | exclusive lock |

## 5 Why / FTA

Delay <- no next-stage watcher <- r35 waiter ends on success <- progression not modeled <- campaign and fleet monitoring conflated. Top event also requires stale status accepted or no live-PID verification; both are closed by the new gate.

## Fishbone

- Method: one-shot script, no phase model.
- Machine: LAVIE shared with tri-track.
- Measurement: generic SUCCESS lacked campaign meaning.
- Software: old waiter encoded obsolete continuous 35 s cooling.
- Governance: no fresh harness evidence required before saying monitored.

## Countermeasures / forbidden

Use atomic status, bounded checks, exclusive lock, explicit next action, and observation-only mode until thermo validation. Forbidden: claiming dedicated monitoring from tri-track alone; reviving the 35 s job; dispatching unvalidated cooling; changing `PROXY_GAP`.

Links: `docs/INCIDENT_LOG.md`, `docs/quality_incident_report_20260803_lavie_pipeline_monitor_gap_inc186.md`.
