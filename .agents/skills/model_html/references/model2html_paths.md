# Model HTML Paths

## Primary files

- `clawstack_v2/data/work/scripts/model2html.py`
- `clawstack_v2/docker/quality_dashboard/app.py`

## Key existing features

- 3 HTML size profiles:
  - `email_2mb`
  - `storage_5mb`
  - `high_quality`
- estimate-only mode
- strict profile limit error for undersized unsafe requests
- ZIP estimate and ZIP download
- decimation quality guard to reject oversized triangles

## Recent design rules

- Do not silently emit oversized HTML for strict profiles.
- If safe simplification cannot meet the target, fail clearly.
- ZIP is a preferred path for email attachment constraints.
- Pre-conversion estimate should be shown to the user when possible.

## Typical change map

- mesh simplification and guard:
  - `model2html.py`
- profile and estimate behavior:
  - `model2html.py`
- Streamlit UI, preview text, ZIP buttons:
  - `quality_dashboard/app.py`
