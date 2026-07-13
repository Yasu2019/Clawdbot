# Moldflow 4-day evaluation readiness — 2026-07-13

## Current outcome

- Dynabook (`DESKTOP-UOVCG4T`, Tailscale `100.98.133.40`) is reachable from K10 by SSH key without a password prompt.
- `MoldflowRemoteAgentV12` remains the enabled logon task. The agent health endpoint and discovery previously passed.
- Moldflow Insight 2010 provides `synergy.exe` and `runstudy.exe`; `studymod.exe` and `studyrlt.exe` are absent.
- CAE Studio API is healthy on `http://127.0.0.1:8776`; the browser app is served at `http://localhost:8088/apps/moldflow_cae_studio/index.html`.
- A metadata-only material inventory contains 530 records: 522 UDB and 8 DAT/CSV/UDB files. It is stored in local SQLite and synchronized to Turso.
- No material property payload, authentication token, SSH private key, or Windows password is stored in this record or Git.

## Implemented paths

- Material manifest: `D:\Clawdbot_Docker_20260125\data\workspace\materials\dynabook_moldflow2010_manifest.json` (runtime data, Git-ignored)
- Material SQLite: `D:\Clawdbot_Docker_20260125\data\workspace\moldflow_materials.db` (runtime data, Git-ignored)
- Importer: `D:\Clawdbot_Docker_20260125\scripts\import_moldflow_materials.py`
- CAE API: `D:\Clawdbot_Docker_20260125\scripts\moldflow_cae_studio_api.py`
- Study creator: `D:\Clawdbot_Docker_20260125\projects\Moldflow2010_Remote_MCP_FullKit\moldflow\vbs\04_create_test_study.vbs`
- Result-log exporter: `D:\Clawdbot_Docker_20260125\projects\Moldflow2010_Remote_MCP_FullKit\moldflow\vbs\05_export_study_logs.vbs`
- Dynabook PP STEP: `G:\MoldflowRemote\workspace\incoming\pp_plate_100x60x2.step`
- Dynabook automation scripts: `G:\MoldflowRemote\workspace\automation\`

## API verification

- `GET http://127.0.0.1:8776/api/health` returned `ok=true`.
- `GET http://127.0.0.1:8776/api/material-inventory?limit=3` returned `total=530`.
- The HTML now cache-busts `app.js` with `v=20260713-evaluation`, preventing the old 8770 client from remaining cached.

## Remaining gate before the 4-day run

Automatic creation of the PP test SDY was attempted twice: once through SSH and once through an interactive-token scheduled task. Moldflow started as an OLE server but did not return from project creation/import and produced no SDY. Both attempts were stopped, the temporary task was deleted, and the leftover Synergy process was terminated. No analysis was launched and no existing study was modified.

This narrows the remaining problem to a visible Synergy dialog or a Moldflow 2010 import option that requires one interactive confirmation. On the next attempt, watch the Dynabook screen while the one-shot task runs, capture the dialog text, and answer only that dialog. After an SDY exists, verify `05_export_study_logs.vbs`, then run one controlled analysis. Keep `agent.json` at `dry_run=true` until that SDY and log export pass.

### Root cause confirmed later on 2026-07-13

Read-only window enumeration and the Windows Application event log confirmed the blocker. Synergy opens the retired Autodesk URL `https://www.autodesk.com/products/moldflow/overview` in its embedded Internet Explorer control. A modal `Internet Explorer_TridentDlgFrame` titled `スクリプト エラー` disables the Synergy main window before `CreateObject("synergy.Synergy")` returns. One COM-launched instance also recorded an `MFC80U.DLL` access violation (`0xc0000005`). The license server, STEP import, and analysis were not reached.

Automatic script-error suppression did not affect the embedded control. A class/PID-restricted close helper was prototyped, but Windows' interactive desktop boundary prevented reliable unattended execution, so it was not installed as a persistent GUI automation path. The safe next action is one manual close of the obsolete Web script-error dialog after Synergy starts; then rerun the COM diagnostic before creating the SDY.

The permanent `MoldflowRemoteAgentV12` task was restored and simplified to start `.venv\Scripts\python.exe -m agent.api --config config\agent.json` directly at `mec21` logon. Final verification: port 8766 listening, health `ok=true`, `dry_run=true`, Synergy process count 0.

## Recovery rules

- Never put tokens, private keys, or passwords into Markdown or `.gitignore`; `.gitignore` contains patterns, not secrets.
- Keep the SSH private key only at `C:\Users\yasu\.ssh\moldflow_remote_ed25519` with restricted ACLs.
- Keep the agent token only in the untracked local `config\agent.json` copies.
- If connectivity fails: confirm Tailscale, SSH port 22, `MoldflowRemoteAgentV12`, then local health on Dynabook, then the K10 tunnel/MCP connection—in that order.

## Version control

- Pre-change safety commit pushed: `17b88c9793` (`backup: preserve Moldflow evaluation baseline`).
- Beads: material/API `adzn`; PP SDY `8rxw`; result extraction `7j1o`.
