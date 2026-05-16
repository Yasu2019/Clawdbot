# Atsugi 3D Render Failure Lessons

Date: 2026-05-16 JST

## Status

Major failures are now recorded, but not every tiny trial image or prompt variation is worth a formal incident entry.

Canonical records:

- `docs/INCIDENT_LOG.md` `INC-078`: buildings floated above terrain.
- `docs/INCIDENT_LOG.md` `INC-079`: road layer visually intersected buildings.
- `docs/INCIDENT_LOG.md` `INC-080`: Hon-Atsugi mecha render used an unposed/static model.
- `docs/INCIDENT_LOG.md` `INC-081`: failure lessons were scattered and needed consolidation.
- `docs/knowledge/atsugi_terrain_grounding_generic_quality_playbook_20260516.md`: reusable terrain/building grounding playbook.
- `services/ai_image_gen/outputs/hon_atsugi_station_front_quality_report.json`: latest station-front image quality gate.
- `projects/AtsugiMechaCity/realistic_city_pipeline/README.md`: partial adoption decision for the realistic city pipeline ZIP.
- `projects/AtsugiMechaCity/asset_search/asset_manifest.json`: licensed Wikimedia photo candidates and source metadata.

## Failure Ledger

| Failure | Symptom | Recorded In | Prevention Gate |
| --- | --- | --- | --- |
| Building float | Buildings looked airborne even after numeric alignment | `INC-078` | Footprint terrain sampling, embed depth, contact pads, close/wide visual review |
| Foundation/pad artifact | Dark pads made the correction look artificial | `INC-078` | Terrain-colored thin pads, avoid heavy black pedestal look |
| Road/building conflict | Road layer appeared under or through large building | `INC-079` | Building exclusion boxes, skipped road-triangle counters, worst-overlap camera |
| T-pose/static model | DOM/mecha looked unposed | `INC-080` | Mixamo posed source, freeze evaluated mesh, reject T-pose silhouettes |
| Axis/import drift | Direct rig import could become horizontal or bounds-broken | `INC-080` and rigging docs | Object filtering, axis sanity, close/wide diagnostic screenshots |
| Low realism / white-box city | Station-front output contained roads/windows/signs but still looked synthetic | `hon_atsugi_station_front_quality_report.json` | Material realism score must reach 3 before release |
| Weak lighting/camera | Scene looked like a debug render rather than photo-like station view | `hon_atsugi_station_front_quality_report.json` | Lighting and camera scores must reach 3; prefer lower photographic lens/camera |
| Weak character integration | DOM is placed but needs stronger foot shadow/contact/AO | `hon_atsugi_station_front_quality_report.json` | Contact shadow/AO gate before final image delivery |
| Stable Diffusion overreach risk | AI can invent station details or erase factual PLATEAU/OSM structure | realistic city pipeline README | Use local SD/OpenVINO for texture/decal/color finish, not whole-scene replacement |
| Google/Street View licensing risk | User-provided Google screenshots cannot be reused as backgrounds/textures | asset search README and realistic city pipeline README | Use only as visual reference; use Wikimedia/Pexels/Pixabay/Unsplash with manifest metadata |
| API/cost anxiety | User is concerned about cloud/API cost | realistic city pipeline config | Default to Wikimedia, Blender, local OpenVINO; use Pexels/Unsplash only when explicitly requested |
| ByteRover memory limit | `brv query/curate` hit free daily request limit | `INC-081` | Local docs are authoritative fallback until ByteRover quota/provider is available |

## Current Quality Baseline

Latest station-front quality report:

- `city_density = 3`: minimum practical density is present.
- `material_realism = 1`: not release-ready.
- `lighting = 2`: basic only.
- `camera = 2`: review composition, not cinematic/photo-like.
- `character_integration = 2`: visible placement, weak contact realism.
- `pass_release_gate = false`.

## Required Next Improvement Order

1. Add facade material variation: concrete, glass, store panels, darker window bands.
2. Add road surface detail: asphalt noise, lane wear, crosswalk dirt, curb color variation.
3. Add station-front clutter: signs, railings, poles, bollards, vending-machine-like blocks, deck underside detail.
4. Add DOM contact realism: stronger contact shadow, ambient occlusion, foot dirt or darkening.
5. Improve camera: lower human/street-level perspective with 35mm/50mm-style framing.
6. Use local OpenVINO/Stable Diffusion only for material/decal/color finishing.
7. Run `evaluate_render_quality.py` and block final delivery if any release score is below 3.

## First-Run Rule For Future 3D Maps

Do not declare a new 3D map "good" after a single successful render.

Minimum first-run acceptance:

- Geometry: terrain/building/road layer conflicts scored and reported.
- Pose: model is non-T-pose, non-horizontal, visibly standing.
- Contact: building and mecha foot contact checked from close and wide views.
- Realism: material, lighting, camera, and character integration scores are at least 3.
- Licensing: external photo/material inputs have source, author, license, and page URL in a manifest.
- Delivery: final image is visually opened before Telegram or user-facing delivery.

