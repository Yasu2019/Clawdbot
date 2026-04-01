# Medium / High Risk Notification Policy

Last updated: 2026-03-29 JST

## Current implementation

- Low risk auto-repair:
  - [`auto_repair_allowed.py`](/D:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed.py)
- Medium / high risk notification:
  - [`risk_notification.py`](/D:/Clawdbot_Docker_20260125/data/workspace/risk_notification.py)
- Latest status:
  - [`risk_notification_status.json`](/D:/Clawdbot_Docker_20260125/data/workspace/risk_notification_status.json)

`idle_ingest_maintenance.py` runs `risk_notification.py` after low-risk auto-repair. Medium / high risk items are notified through Telegram first and Gmail second, with duplicate suppression via `risk_notification_state.json`.

## Principle

Medium and high risk findings must be notified, not auto-fixed.

## Medium risk

Examples:
- long timeout or stuck nightly pipeline
- stale status that cannot be safely healed by retry alone
- low-risk auto-repair action failure
- `iatf_seed_auto_update.py` detects `changed_existing > 0`

Handling:
- do not overwrite automatically
- persist status JSON
- notify through Telegram and Gmail
- keep enough detail for manual review

## High risk

Examples:
- compose-level failures
- shared service corruption
- cross-org policy violations
- SDK or license issues
- auth / API key / permission breakage

Handling:
- do not auto-fix
- persist status JSON
- notify through Telegram and Gmail
- wait for explicit operator judgement

## Channels

- Primary: Telegram
- Secondary: Gmail
- Local visibility: Portal / Learning Memory / Auto Repair Console

## Auto-diff specific rule

When `iatf_seed_auto_update.py` reports `changed_existing > 0`:

- treat it as medium risk
- show it in the Rails update history page
- send Telegram/Gmail notification through `risk_notification.py`
- do not replace the existing seed/live file automatically
