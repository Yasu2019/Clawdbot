---
title: Fleet Operations 7 Node Status
created: 2026-06-10
updated: 2026-06-10
tags:
  - fleet
  - operations
  - monitoring
  - k10
  - obsidian
source:
  - Growth Dashboard Fleet Diagnostics
  - Beads fleet diagnostics memories
  - monitor_agent diagnostics
---

# Fleet Operations 7 Node Status - 2026-06-10

## Purpose

This note is the human-readable operations room for the 7-PC Clawstack fleet.

Obsidian should help humans and AI models share context, but it is not the only source of truth.

- Live state: `data/workspace/apps/growth_dashboard/fleet_diagnostics_status.json`
- Task history: Beads
- Code and rollback: GitHub
- Local 24h evidence: each node's `monitor_agent` diagnostics
- Human-readable synthesis: this Obsidian note

## Current Fleet

| Node | Role | Current Stability | Recommended Work |
|---|---|---|---|
| K10 / NucBox | Main orchestrator, dashboard, routing | Diagnostics OK via fallback `8112`; LHM still not trusted | Control, monitoring, short orchestration jobs |
| Red LAVIE | Dedicated medium-heavy Windows worker | Diagnostics OK on `8111`, LHM OK | Preferred offload for CAE batches, document processing, render helpers |
| ThinkPad L590 Ubuntu | SSH node, Linux worker | SSH reachable; metrics path separate from Windows monitor_agent | Linux setup, OpenFOAM/OpenRadioss experiments, bounded automation |
| Dynabook | Light helper node | Metrics OK on `8111`; diagnostics OK via fallback `8112`; warm node | Light helper jobs only, avoid sustained heavy load |
| Vivobook / mhn15 | User daytime work PC | Restored on 2026-06-10; metrics and diagnostics OK on `8111` | Light only, especially 08:00-19:00 |
| LAVIE normal | CAE candidate, but unstable | Currently manual check required; previous BIOS/offline incident | Hold heavy work until local power/startup and diagnostics are restored |
| G3 node | Stable helper / satellite | Not in latest diagnostics audit table; historically used as light-medium helper | Queue checks, scraping, bounded document processing |

## Most Recent Diagnostic Result

As of 2026-06-10 around 12:25 JST:

- OK: K10, Red LAVIE, Dynabook, Vivobook
- Manual check: LAVIE normal
- Special handling:
  - K10 uses fallback diagnostics on `8112`
  - Dynabook uses fallback diagnostics on `8112`
  - Vivobook was successfully restored by running `setup_monitor_node.ps1`

## Operating Rules

1. Do not treat a node as RCA-ready unless `/diagnostics` is online.
2. `/metrics` alone is not enough for root cause analysis.
3. If Windows `8111` is held by an old access-denied process, use diagnostics fallback `8112`.
4. Do not assign heavy work to mhn15 during daytime business hours.
5. Do not fall back heavy CAE from Red LAVIE to normal LAVIE while normal LAVIE is unstable.
6. Keep Dynabook on light duty when temperature rises above 80C.
7. Keep each major operational change documented in Beads, Git, and this vault when it changes fleet behavior.

## Information Sharing Between PCs

Use this split:

- K10 writes live JSON and dashboard data.
- Nodes write 24h local diagnostics and upload fleet evidence when possible.
- Obsidian stores reviewed summaries, RCA lessons, and stable operating rules.
- Beads stores tasks and durable short memories.
- GitHub stores code, scripts, and rollback points.

This prevents one PC or one tool from becoming the only place where knowledge exists.

## Information Sharing Between AI Models

Model handoff should be explicit and source-backed.

| Model / Agent Type | Best Use | Handoff Output |
|---|---|---|
| Codex | Code changes, scripts, dashboard, diagnostics, Git | Commit, incident log, Beads memory |
| Local small model | Quick summaries, low-cost classification | Draft summary only |
| Cloud stronger model | Design review, hard RCA, complex planning | Reviewed proposal or RCA note |
| RAG / Qdrant | Search previous knowledge | Cited snippets, not final decision alone |
| Obsidian | Human-readable memory and reasoning map | Reviewed notes and hubs |

## Next Actions

- Restore normal LAVIE monitor_agent and diagnostics.
- Add G3 to `k10_fleet_diagnostics_audit.py` if it is still part of the 7-node active fleet.
- Add a small daily note template for fleet changes if manual review becomes frequent.
- Keep Growth Dashboard as the first live status view, and Obsidian as the reviewed knowledge view.

## Related

- [[Fleet_Operations_Hub]]
- [[OpenClaw_Obsidian_Guide]]
- [[AI_Inbox]]

