# Radius100 UE5 Compare Report

Date: 2026-05-21 JST

## Goal

Run the mini-PC safe UE5 background test:

- radius 100m
- city-only split assets
- 1280x720 still comparison
- road PBR first
- low-angle camera
- SceneCapture2D standard output

## Expected Outputs

- `radius100_compare/r100_baseline.exr`
- `radius100_compare/r100_pbr_road.exr`
- `radius100_compare/r100_pbr_road_building_props.exr`
- PNG previews converted from the EXR files
- `radius100_compare/radius100_ue5_compare_report.json`
- `radius100_compare/r100_contact_sheet.png`

## Pass Criteria

- Black background is avoided.
- Road surface is visible from the low-angle camera.
- Buildings are not only a single gray material in the final comparison.
- Bounds are close to a 100m city slice, not full-city or mecha-sized.
- The three PNG previews are easy to compare side by side.

## Current Judgment

Run completed.

## Results

- Blender split export: passed.
- UE5 import/render: passed.
- Resolution: 1280x720.
- Render method: SceneCapture2D + TextureRenderTarget2D + EXR export.
- EXR to PNG conversion: passed.
- Contact sheet: generated.
- API cost: none, local Blender + local UE5 only.
- Composition v2: completed.

## Output Files

- `plateau_export/radius100_split/radius100_split_export_report.json`
- `radius100_compare/radius100_ue5_compare_report.json`
- `radius100_compare/r100_baseline.png`
- `radius100_compare/r100_pbr_road.png`
- `radius100_compare/r100_pbr_road_building_props.png`
- `radius100_compare/r100_contact_sheet.png`

## Observations

- The mini-PC safe pipeline now works end to end.
- The camera is no longer below the road layer.
- The black-background problem improved after adding an explicit sky backdrop.
- The final image still does not meet photoreal quality, but the street composition is now materially better than the first radius100 pass.
- PLATEAU geometry remains too box-like.
- Road visibility improved after adding a foreground 3D asphalt proxy, lane stripes, crosswalk strips, curbs, proxy facades, cars, signs, and poles.
- `Signs.fbx` was not exported because no sign faces existed inside the radius100 slice.
- The large PLATEAU window actor is hidden in the final comparison to avoid the unrealistic single blue-wall look.

## Next Fix

Do not proceed to video yet. The next still-image fix should:

- choose a better street-center camera target,
- reduce foreground obstruction further,
- add stronger asphalt/sidewalk contrast and texture scale,
- add more nearby props at visible scale,
- crop or hide buildings that block the entire right edge,
- keep the same 3-image comparison loop.
- add a generated or local PBR wall texture to proxy facades,
- add visible shop signs and traffic light colors.
