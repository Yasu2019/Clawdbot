---
title: Fleet Operations Hub
created: 2026-06-10
updated: 2026-06-10
tags:
  - fleet
  - hub
  - operations
  - ai-coordination
---

# Fleet Operations Hub

## Role

This hub connects the Clawstack PC fleet, AI model roles, and operational memory.

Use it as the starting point when deciding:

- which PC should receive a job
- whether a node is stable enough
- where to write the result
- which AI model should handle the next step

## Canonical Links

- Live dashboard: `http://localhost:8088/apps/growth_dashboard/index.html`
- Fleet diagnostics JSON: `data/workspace/apps/growth_dashboard/fleet_diagnostics_status.json`
- Fleet status note: [[Fleet_Operations_7_Node_Status_20260610]]
- General Obsidian guide: [[OpenClaw_Obsidian_Guide]]

## Node Groups

### Main Control

- K10 / NucBox

### Preferred Work Nodes

- Red LAVIE
- ThinkPad L590
- G3 node

### Light / Protected Nodes

- Vivobook / mhn15
- Dynabook

### Hold / Repair

- Normal LAVIE until diagnostics are restored

## Decision Checklist

Before assigning work:

1. Check Growth Dashboard diagnostics.
2. Confirm `/diagnostics` is online or SSH metrics are current.
3. Check temperature, CPU, RAM, and last event.
4. Match job class to node class.
5. Record important changes in Beads and this vault.

## Job Class Routing

| Job Class | First Choice | Avoid |
|---|---|---|
| Orchestration / dashboard | K10 | Heavy CPU jobs on K10 |
| Medium CAE / batch | Red LAVIE | Normal LAVIE while unstable |
| Linux tooling / OpenFOAM | ThinkPad | Vivobook daytime |
| Light scraping / checks | G3, Dynabook | Dynabook if hot |
| Daytime human work support | Vivobook | Heavy background jobs |

## Operating Memory Rule

Obsidian is the reviewed knowledge layer.

Do not use it as a replacement for:

- Beads task tracking
- Git commits
- JSON status files
- local node diagnostics
- incident logs

Instead, use Obsidian to explain why the system is configured that way.

