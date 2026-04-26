# GD&T Overlay Studio

3D model and drawing workbench for combining geometric tolerances with a browser-based 3D viewer.

## Current scope

- 3D model input: `STL / OBJ / GLB / GLTF`
- Drawing input: `PDF / PNG / JPG / SVG / DXF`
- Packed HTML import: `gdt_packed_iso_*.html`
- Manual datum and GD&T editing
- Session JSON export and import

## DXF preview reuse

DXF preview reuses the existing `dxf2step` API:

- `POST /api/dxf2step/jobs`
- `GET /api/dxf2step/preview-svg/{job_id}`

## Limitation

Direct `STEP` import is not included in this MVP.
The intended path is to pair it with the existing `STEP -> 3D HTML` or `STEP -> STL` workflow.

## Protocol reference

The UTF-8 BOM-safe protocol package is stored at:

`D:\Clawdbot_Docker_20260125\local_llm_supervision_protocol_complete_utf8_bom.zip`

This app's local summary is:

- [`PROTOCOL_REFERENCE.md`](/D:/Clawdbot_Docker_20260125/data/workspace/apps/gdt_overlay_studio/PROTOCOL_REFERENCE.md)
