---
name: model_html
description: "Use when working on STEP/STL to 3D HTML conversion, HTML size profiles, ZIP export, mesh simplification, or quality_dashboard model conversion UI in this project. Inspect model2html.py and quality_dashboard app.py first, preserve shape before size reduction, and validate estimates, profiles, and downloads together."
---

# Model HTML Skill

Use this skill for 3D HTML export, STL/STEP viewer quality, size profile enforcement, ZIP generation, and model simplification safety.

## Workflow

1. Read the main files first:
   - `clawstack_v2/data/work/scripts/model2html.py`
   - `clawstack_v2/docker/quality_dashboard/app.py`
2. Identify which layer the change belongs to:
   - mesh processing
   - profile / estimate logic
   - Streamlit UI and downloads
3. Preserve geometry before shrinking output size.
4. If simplification produces suspicious triangles or distorted shape, reject the simplification result.
5. When changing output size behavior, update:
   - estimate logic
   - strict profile decision
   - actual download behavior

## Rules

- Shape-preserving output is more important than hitting an aggressive size target.
- For email-size use cases, prefer ZIP support rather than destructive decimation.
- Keep estimate-only paths cheap and deterministic.
- Validate both HTML and ZIP expectations.

## Validation

- `python -m py_compile clawstack_v2/data/work/scripts/model2html.py clawstack_v2/docker/quality_dashboard/app.py`
- estimate-only output still returns JSON
- UI still supports profile selection and downloads

## Read next

- For key paths and recent decisions: `references/model2html_paths.md`
