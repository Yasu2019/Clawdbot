# Integration Playbook

## Goal
Make the added local services work as one operating surface instead of isolated UIs.

## Current Integration Loops

### Documents
1. Use `Stirling PDF` for cleanup, merge, split, OCR repair.
2. Drop results into `clawstack_v2/data/paperless/consume`.
3. Let `Paperless` archive the documents.
4. For mail input, use the host-side EML pipeline to generate `TXT/HTML/PDF/knowledge`.

### Monitoring
1. Track sites in `changedetection`.
2. Host-side bridge sends change alerts into local `ntfy`.
3. The same bridge creates tasks in `Vikunja` project `Changedetection Inbox`.
4. The bridge also posts the normalized event into `n8n` webhook `changedetection-bridge`.
5. `n8n` republishes an automation intake alert for traceability and future fan-out.

### Media
1. Store photo/video material in `Immich`.
2. Use `ntfy` for service-health or sync alerts.

## Operational Hub
- Main hub: `Dashy`
- Health watcher: `scripts/watch_app_mesh.ps1`
- Health status:
  - `data/state/app_mesh/harness_status.json`
  - `data/state/app_mesh/state.json`

## Commands
- Start health watcher:
  `powershell -ExecutionPolicy Bypass -File scripts/start_app_mesh_watch.ps1`
- Check health watcher:
  `powershell -ExecutionPolicy Bypass -File scripts/check_app_mesh.ps1`
- One-shot probe:
  `powershell -ExecutionPolicy Bypass -File scripts/watch_app_mesh.ps1 --once`
- Start Changedetection bridge:
  `powershell -ExecutionPolicy Bypass -File scripts/start_changedetection_bridge.ps1`
- Check Changedetection bridge:
  `powershell -ExecutionPolicy Bypass -File scripts/check_changedetection_bridge.ps1`
- Setup n8n intake flow:
  `powershell -ExecutionPolicy Bypass -File scripts/setup_n8n_changedetection_flow.ps1`
- Check n8n intake flow:
  `powershell -ExecutionPolicy Bypass -File scripts/check_n8n_changedetection_flow.ps1`

## Rules
- Keep integration host-side when possible.
- Prefer `ntfy` as the first shared notification bus.
- Prefer `Dashy` as the first shared human entry point.
- Do not put private email content into ByteRover.
