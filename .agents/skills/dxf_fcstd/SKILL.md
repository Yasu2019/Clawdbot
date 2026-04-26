---
name: dxf_fcstd
description: "Use when working on DXF, FCStd, STEP, or FreeCAD conversion in this project. Reuse the existing apps/dxf2step pipeline first, inspect dxf2step_api.py and dxf2step_worker.py before changing anything, and prefer extending current outputs, job flow, and FreeCADCmd execution rather than creating a new converter."
---

# DXF to FCStd Skill

Use this skill for DXF, FCStd, STEP, FreeCAD, layer-based extrusion, and DXF multi-view reconstruction tasks.

## Workflow

1. Confirm overlap with the existing app:
   - `data/workspace/apps/dxf2step/`
   - `data/workspace/apps/dxf_fcstd_protocol/`
2. Read the key files first:
   - `data/workspace/apps/dxf2step/dxf2step_api.py`
   - `data/workspace/apps/dxf2step/dxf2step_worker.py`
   - `data/workspace/apps/dxf2step/index.html`
3. Check whether the request belongs in:
   - API output listing
   - FreeCAD worker export logic
   - UI labels / download links
4. Extend the existing pipeline instead of creating a parallel app unless the current job model is incompatible.
5. Validate with:
   - `python -m py_compile data/workspace/apps/dxf2step/dxf2step_api.py data/workspace/apps/dxf2step/dxf2step_worker.py`
   - output file presence in the job `output/` directory

## Rules

- Reuse `docker exec ... FreeCADCmd` via the current worker.
- Preserve current job folder structure under `data/workspace/apps/dxf2step/jobs/`.
- When adding output formats, update both worker export and API output listing.
- Prefer `FCStd + STEP + preview PNG` as a coherent output set.

## Read next

- For key paths and decisions: `references/dxf2step_paths.md`
