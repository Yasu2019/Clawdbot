# App page FACT bar -- CETOL / VIAI / CAE labs (2026-08-27)

IDs: INC-189 / T082 / S033 / bd `app-page-fact-bar-cetol-viai-20260827`

## 1. Goal

Per-app Portal pages must show dated FACT from live JSON, not hardcoded SUCCESS or commercial-parity wording. User time is spent looking at localhost pages; stale or silent-broken JS is a false picture.

## 2. Context

- Portal nginx: `portal_server` maps `data/workspace` -> `http://127.0.0.1:8088`
- Visual Inspection AI is **not** on 8088. It is FastAPI on `http://127.0.0.1:18010/` (`projects/visual_inspection_ai`, StaticFiles `/ui`)
- CETOL reports JSON: `data/workspace/apps/cetol6sigma/cetol_reports.json` (K10 `cetol_app_report_builder.py`)
- CETOL golden: `data/workspace/cetol_golden_status.json` (daily 07:40 `cetol_golden_regression.py`)
- OpenFOAM evolution: `data/workspace/cae_trial_evolution_state.json`
- Tri-track: `data/workspace/k10_tri_track_cae_status.json` (mirror under `apps/growth_dashboard/`)
- OpenRadioss INC-188 snapshot: `data/workspace/openradioss_inc188_status.json`
- Truth Gate / T019 / P025 / P026 apply. Do not label commercial Moldflow / Cetol 6 Sigma / AOI / shear sign-off.

## 3. Observed facts (browser 2026-08-27)

| Page | FACT shown after fix |
|---|---|
| `/apps/cetol6sigma/index.html` | golden PASS 2026-08-26 max_err=0.512% (g1/g2/g3 1D stack); reports 2026-07-15 30件 STALE |
| `/apps/moldflow_cae_studio/index.html` | fill 99.55% complete=1 at 2026-08-23 trial `tri-lavie-resin_fill_cad-481b8240`; loop SKIP_STORAGE (F free ~6.4%) |
| `http://127.0.0.1:18010/` | inspections=34 reviews=14 Champion=1; P027 visual_inspection n=1 awaiting_human machine_verified=0 |
| `/apps/fem_impact/index.html` | last_success 2026-07-31 `tri-thinkpad-fem_impact-2aaf6338`; last SKIP_STORAGE |
| `/apps/openradioss_lab/index.html` | last_success 2026-07-01; INC-188 IN_PROGRESS; round hole phi 0.56 mm open; container sleep infinity |

CETOL before fix: `#liveEvidence` stayed on "読込中", `#empty` stayed on "cetol_reports.json を読み込んでいます", `typeof fmt === "undefined"`. `cetol_reports.json` HTTP 200 size=260064 in 0.22s. `node --check` on extracted script: `SyntaxError: Unexpected token 'else'`.

Root location: `apps/cetol6sigma/index.html` snap_fit branch closed, then a duplicate shaft_bearing animation block, then `} else if (connectorMode === "bolt_joint"`. Valid `shaft_bearing` branch already existed earlier in `animate()`.

## 4. Hypotheses (labeled)

- H1 (confirmed): giant inline script parse failure blocked report fetch and FACT fill.
- H2 (confirmed): reports JSON STALE is independent of golden PASS; both must be shown.
- H3 (open): K10 `cetol_app_report_builder` not refreshing reports since 2026-07-15.

## 5. Decision rule

IF a Portal/app page is a status surface THEN fetch live JSON and print FACT with timestamp + trial_id + STALE/SKIP if aged.

IF `typeof keyFn === "undefined"` on a page that should have loaded reports THEN run `node --check` on the extracted inline script; do not assume JSON 404.

IF FACT UI is inside a 2000-line inline script THEN a parse error anywhere kills the FACT bar. Prefer a tiny independent IIFE next to the bar, or keep the giant script syntactically valid.

IF golden / KPI JSON PASS THEN still write "not commercial X" on the same bar. Golden 1D stack is not Cetol 6 Sigma. fill_complete=1 OpenFOAM is PROXY not Moldflow. Champion count is not MSA.

## 6. Procedure

1. Confirm `portal_server` on :8088. Do not stop OpenRadioss container.
2. For 8088 apps, fetch `../../<status>.json` from `apps/<name>/index.html`.
3. For VIAI, fetch same-origin `/api/health` and `/api/metrics` (CORS not needed).
4. CETOL: also fetch `../../cetol_golden_status.json`. Keep reports age warning (>24h).
5. After HTML/JS edit: `node --check` extracted `<script>` if the page has a giant inline script.
6. Browser: read `#liveEvidence` / `#factBar` innerText. HTTP 200 of index.html is not enough.
7. Portal cards must match the same FACT sentence.

## 7. Verification

- CETOL: combobox lists 30 jobs AND FACT bar contains `golden PASS` and `STALE`.
- Moldflow: FACT contains `fill=99.55` and `complete=1` and does not call 2026-08-03 63.6% a current success.
- VIAI: FACT inspections count equals sum of `/api/metrics` decisions (34 = 20 OK + 14 NG).
- FEM / OpenRadioss: last_success timestamps match tri-track / inc188 JSON.
- Encoding: UTF-8 readback, no U+FFFD, no cp932 mojibake glyphs.

## 8. Failure signatures

- `fmt` / `DATA` undefined, empty "読み込んでいます" forever: inline script SyntaxError.
- FACT bar "読込中" while headings exist: hidden `#content` in a11y tree; fetch never ran.
- Golden PASS used as "Cetol equivalent": Truth Gate violation.
- VIAI 8088 URL: wrong process; must use :18010.
- Tri-track last_success 2026-08-03 fill 63.6% with fill_complete=0 presented as current OF success: P026 violation.

## 9. Recovery / rollback

- Git branch `backup/pre-cetol-viai-fact-20260827` taken before FACT edits.
- Revert only `apps/cetol6sigma/index.html` if 3D connector demo regresses; FACT independent IIFE can stay.
- Reports refresh: run K10 `scripts/cetol_app_report_builder.py` (does not change golden).

## 10. Scope limits

- Did not regenerate `cetol_reports.json`.
- Did not claim commercial solver parity.
- Did not start OpenRadioss compute or free F: drive.
- VIAI 3D depth remains uncalibrated; FACT says so.
- graphify full-repo hook historically times out at 600s; this record is a bounded add/update.

## 11. Next experiment

Run `cetol_app_report_builder.py` once and confirm `generated_at` moves off 2026-07-15 without changing golden 1D numbers. Keep STALE logic.

## 12. Provenance

- Date: 2026-08-27 JST (record 2026-08-28)
- Pages: cetol6sigma, moldflow_cae_studio, fem_impact, openradioss_lab, visual_inspection_ai/ui, portal.html
- JSON: cetol_golden_status.json, cetol_reports.json, cae_trial_evolution_state.json, k10_tri_track_cae_status.json, openradioss_inc188_status.json, p027_evaluation_state.json
- Commit: see git log after this recording session
- bd: `app-page-fact-bar-cetol-viai-20260827`
- INC-189 / T082 / S033
