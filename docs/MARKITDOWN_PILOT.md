# MarkItDown Pilot

Date: 2026-04-12
Status: pilot-safe
Scope: manual, read-only, non-daemon trial on the mini PC

## Purpose

This pilot allows limited local document-to-Markdown conversion using `markitdown` without:

- changing `docker-compose*.yml`
- adding a watcher
- adding a daemon
- wiring directly into Paperless, Gmail, or automated ingest

## Files

- Script: `data/workspace/scripts/run_markitdown_pilot.ps1`
- Input folder: `data/workspace/inputs/markitdown_pilot/raw_docs`
- Output folder: `data/workspace/outputs/markitdown_pilot/processed_md`
- Logs: `data/workspace/outputs/markitdown_pilot/logs`

## Safety Rules

- Manual run only
- Read from the pilot input folder only
- Write to the pilot output folder only
- Max 20 files per run by default
- No overwrite unless `-Overwrite` is passed
- No auto-import into any existing ingestion flow

## First Run

Install `markitdown[pdf]` if the command is not available:

```powershell
pip install "markitdown[pdf]"
```

Run the pilot:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\data\workspace\scripts\run_markitdown_pilot.ps1
```

Optional overwrite:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\data\workspace\scripts\run_markitdown_pilot.ps1 -Overwrite
```

Optional smaller batch:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\data\workspace\scripts\run_markitdown_pilot.ps1 -MaxFiles 5
```

## Adoption Gate

Only consider moving beyond this pilot if all of the following are true:

1. conversion quality is useful on real files
2. no new CMD popup or freeze behavior appears
3. operator effort is lower than the current manual path
4. integration can be done by extending an existing script rather than adding a new always-on service

Until then, this remains a manual utility only.
