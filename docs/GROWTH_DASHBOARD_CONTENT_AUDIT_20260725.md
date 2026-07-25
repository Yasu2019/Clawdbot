# Growth Dashboard Content and Access Audit

Date: 2026-07-25 JST  
Beads: `Clawdbot_Docker_20260125-79wx`

## Goal

Verify that Growth Dashboard reads the latest available application/status
sources and that every listed article, application, video, and document has a
working view or download path.

## Context

- Page: `http://localhost:8088/apps/growth_dashboard/index.html`
- Source: `data/workspace/apps/growth_dashboard/index.html`
- Web server: `clawstack-unified-portal_server-1` (`nginx`, port 8088)
- Asset audit: `data/workspace/apps/growth_dashboard/asset_access_audit.json`

## Observed facts

| Check | Result |
|---|---:|
| Content catalog entries | 18 |
| Catalog asset paths | 48/48 present |
| Approval queue bodies/previews | 5/5 present |
| Current indexed IATF videos | 12/12 present and HTTP-readable |
| Total audited assets | 77/77 present |
| Dynamic dashboard JSON endpoints | 19/19 HTTP 200 and valid JSON |
| Classic inline JavaScript syntax | PASS |
| Portal page HTTP response | 200 |

Five data files had not changed for more than 48 hours at the audit time:
`fleet_diagnostics_status.json`, `distributed_scheduler_status.json`,
`content_publishing_catalog.json`, `trend_content_status.json`, and
`content_approval_queue.json`. This means "unchanged", not automatically
"incorrect". The dashboard now exposes this fact instead of silently implying
that every source was recently regenerated.

The current DXF-to-3D dashboard export was regenerated from its live trial log:
114/114 parts tried, 1,805 trials, and the latest Excel report was produced.
IATF video QA indexing was also refreshed and now exposes 12 canonical videos.

## Changes

1. Replaced broken repository-relative incident links with Web-served mirrors.
2. Hid browser-blocked `file://` links and added Web-safe view/download buttons.
3. Added explicit view/download controls to every content-catalog asset.
4. Added article preview and source-download controls to approval and trend rows.
5. Added explicit view/download controls to IATF video cards.
6. Mounted `data/iatf_videos` read-only in the existing port-8088 Nginx service.
7. Added a repeatable asset mirroring/audit script and visible audit summary.
8. Corrected a missing `<table>` opening tag in the content catalog section.

## Decision rule

IF an asset is listed on the dashboard, THEN it must resolve through HTTP from
the portal or expose a same-origin download, BECAUSE `file://` paths and
unmounted repository paths are not reliably accessible from an HTTP page.

IF a source has not changed for more than 48 hours, THEN show it as unchanged
rather than claiming freshness, BECAUSE age alone does not prove either
correctness or failure.

## Reproduction

1. Run `python scripts/update_growth_dashboard_asset_access.py`.
2. Confirm `missing_assets` is zero in `asset_access_audit.json`.
3. Request every `rows[].url` through port 8088.
4. Validate all dashboard JSON fetch targets parse as JSON.
5. Verify each article/application/video/document section has an explicit
   view or download action.

## Recovery

- Web mirror rollback: remove `downloads/` and restore the prior HTML links.
- Video serving rollback: remove only the read-only `iatf_videos` mount and
  recreate `portal_server`.
- The source documents and videos are never modified by the audit script.

## Scope limits

The in-app browser connector was unavailable, so pixel-level and click-level
visual QA was not performed in that surface. HTTP responses, JSON validity,
asset existence, generated link coverage, and JavaScript syntax were verified.
External third-party links were not treated as locally controlled assets.
