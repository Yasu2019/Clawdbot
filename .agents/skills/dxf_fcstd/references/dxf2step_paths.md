# DXF to FCStd Paths

## Primary files

- `data/workspace/apps/dxf2step/dxf2step_api.py`
- `data/workspace/apps/dxf2step/dxf2step_worker.py`
- `data/workspace/apps/dxf2step/index.html`
- `data/workspace/apps/dxf2step/card.json`
- `data/workspace/apps/dxf_fcstd_protocol/index.html`

## Existing behavior

- `dxf2step_api.py` owns job creation, status, outputs, and file download routes.
- `dxf2step_worker.py` owns FreeCAD script generation and reconstruction logic.
- `dxf2step` already uses `docker exec clawstack-unified-clawdbot-gateway-1 FreeCADCmd`.
- Current output directory is `data/workspace/apps/dxf2step/jobs/<job_id>/output/`.

## Typical change map

- Add new export format:
  - worker export section
  - API `list_outputs`
  - UI download list
- Change reconstruction behavior:
  - `generate_reconstruction_script`
  - `reconstruct_multiview`
- Change single-layer extrusion behavior:
  - `generate_freecad_script`

## Validation checklist

- `py_compile` passes
- API still returns job status
- output directory contains expected files
- combined outputs sort first in the UI when applicable
