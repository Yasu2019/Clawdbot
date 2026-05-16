# Realistic 3D City Pipeline for AtsugiMechaCity

## Adoption Decision

Status: ADOPT_PARTIAL.

The ZIP package `ZIP_Group/opencraw_realistic_3d_city_pipeline_full.zip` matches the current direction for Hon-Atsugi renders: use PLATEAU / OSM / Blender / UE5 / local OpenVINO as a reusable 3D-world pipeline, and avoid Google Maps or Street View image reuse.

This folder implements the safe first step only:

- Keep the current Blender and local OpenVINO workflow.
- Add a reusable quality gate for city density, material realism, lighting, camera, and character integration.
- Use user-provided station photos only as visual reference, not as image textures or backgrounds.
- Leave Docker, Portal, and UE5 project settings unchanged.

## Existing Assets Reused

- `projects/AtsugiMechaCity/render_hon_atsugi_station_front_scene.py`
- `projects/AtsugiMechaCity/render_hon_atsugi_osm_station_scene.py`
- `services/ai_image_gen` local OpenVINO service
- `projects/AtsugiMechaCity/AtsugiMechaCity.uproject`
- `projects/AtsugiMechaCity/diagnostics/`

## No-Go Rules

- Do not scrape Google Maps or Street View.
- Do not paste Google screenshots into the render as a background.
- Do not replace the whole background with a hallucinated AI image when station accuracy matters.
- Do not modify Docker Compose, Portal, or UE5 settings without a separate implementation plan.
- Do not send large cloud API jobs without explicit cost notice and consent.

## Recommended Render Flow

1. Build the scene from PLATEAU / OSM / procedural geometry.
2. Add density: windows, signs, white lines, crosswalks, curbs, bollards, lamps, deck structures, rooftop details.
3. Render a clean 3D background and a DOM/mecha cutout separately.
4. Apply local OpenVINO / Stable Diffusion only as light finish, texture generation, or color grading.
5. Composite the DOM/mecha back into the checked scene.
6. Run `evaluate_render_quality.py` and keep the JSON report with the output image.

## Current Limitation

The latest station-front image has the right structural direction, but still scores low on material realism because buildings remain simple white geometry. The next high-value improvement is facade material/detail generation rather than another full-scene AI pass.

