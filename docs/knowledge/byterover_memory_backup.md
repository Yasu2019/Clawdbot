---
title: ByteRover Memory Backup
tags: [byterover, memory, github-backup]
importance: 80
maturity: operational
createdAt: '2026-05-20T00:00:00+09:00'
---

# ByteRover Memory Backup

This file mirrors important ByteRover curate contexts into a Git-tracked
Markdown document. It exists so operational knowledge survives local PC
failure even when .brv/ is ignored by Git.

## 2026-05-20 11:18:55 +09:00

**Curate status:** completed

**Reason:** brv curate completed successfully

**Context**

verification 2026-05-20: safe curate completed status is now recognized before fallback handling.

**Source files**

- none

## 2026-05-20 15:33:18 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

CityCharacterPipeline 2026-05-20: standardized photoreal/video rendering with --render-profile preview/standard/photoreal and --camera-angle config/hero/street_low/telephoto/orbit. Removed legacy BLENDER_EEVEE_NEXT animation override because Blender 5.1 supports BLENDER_EEVEE/CYCLES and the later override broke profile selection. Added ffmpeg MP4 assembly after successful animation frames. Verified preview MP4 Shibuya_RickDias_Photoreal_walk.mp4: H.264 854x480 90 frames 3.0 sec.

**Source files**

- projects/CityCharacterPipeline/run_pipeline.py,projects/CityCharacterPipeline/configs/photoreal_video.yaml,docs/knowledge/city_character_photoreal_standard_20260520.md,docs/INCIDENT_LOG.md

## 2026-05-20 15:49:44 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

INC-090 2026-05-20: Email nightly MEDIUM risk was caused by phase6_turso_metrics using a Linux venv path that does not exist in the n8n container, while the mounted venv only has Windows Scripts/python.exe. Fixed run_email_rag_ingest_report.py and generate_growth_video.py to ignore .exe candidates on Linux and fall back to python3. get_turso_metrics.py now returns status=degraded with exit code 0 when libsql_client or Turso credentials are unavailable, so optional Turso metrics do not mark the core nightly email report as failed. Verified in container: get_turso_metrics returns degraded JSON rc=0, growth video skips cleanly, and risk_notification.collect_findings returns [].

**Source files**

- none

## 2026-05-20 20:42:15 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

CityCharacterPipeline photoreal facade render result 2026-05-20: enhanced background-building pass completed with configs/photoreal_video_short.yaml. Procedural facade details applied to 9 nearby OSM buildings. Output MP4: projects/CityCharacterPipeline/output/photoreal_video_short/Shibuya_RickDias_Photoreal_Short_walk.mp4. ffprobe: h264 1920x1080 10fps 30 frames 3.0s size 1544605 bytes. Blender/Cycles render time 3580.1s. QA PASS. Telegram sent successfully as message_id=4707. External generation APIs were not used; only Telegram delivery used network.

**Source files**

- none

## 2026-05-20 22:48:28 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

CityCharacterPipeline background realism fix 2026-05-20: previous facade_details were too subtle and one facade panel stayed in the walking corridor after the OSM building was hidden, so the background looked unchanged or was occluded. Fixed material_enhancements.py by overriding road/traffic/facade injection code: real geometry crosswalks/stop lines/lane guides, foreground traffic lights moved to road sides, large readable sign text, glass facade panels, and skip signs/glass for buildings in the walk corridor. Config photoreal_video_short.yaml now enables explicit traffic light positions and stronger facade options. Verified preview and photoreal render. Photoreal output: h264 1920x1080 10fps 30 frames 3.0s size 1669947 bytes, render time 3796.9s, QA PASS. Telegram message_id=4712. Commit afc6bd1 passed CI run 26163240376.

**Source files**

- projects/CityCharacterPipeline/pipeline/material_enhancements.py
- projects/CityCharacterPipeline/configs/photoreal_video_short.yaml

## 2026-05-20 23:30:34 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

CityCharacterPipeline free local img2img photoreal background test 2026-05-20: Best free effect used existing services/ai_image_gen OpenVINO DreamShaper LCM img2img, no external generation API. Direct API auto-resize to 768x432 caused HTTP 500 because dimensions were not 64-aligned. Fix was to pre-resize frames to 640x384, send max_dimension=9999, strength=0.52, steps=6, guidance=1.3, then resize back to 1920x1080. To preserve the robot, SD output was composited only into background using a simple red/central robot mask. Processed 30/30 frames, about 12.6 min total, output MP4 projects/CityCharacterPipeline/output/photoreal_img2img_free_test/RickDias_free_local_img2img_bg_001.mp4, h264 1920x1080 10fps 3.0s, Telegram message_id=4713. Result is much more photorealistic in background, with expected limitations: temporal background flicker and some robot-edge blending.

**Source files**

- none

## 2026-05-20 23:48:53 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

2026-05-20 CityCharacterPipeline photoreal background improvement: local SD/img2img improved texture but flickered and mutated geometry. Higher realism came from real photo plate compositing: use a free photo plate (Pixabay id 5655593 by djedj), render Blender foreground alpha pass with all non-character meshes hidden and film_transparent RGBA, then composite high-quality Cycles robot RGB over the photo using the alpha mask. Best settings in output/real_photo_plate_video: v4 clean matte, robot shifted down 72px, tight upper matte, grown lower matte, soft contact shadow, slight road-color dust tint, outdoor photo color grading. Output RickDias_real_photo_plate_v4_clean.mp4 sent to Telegram message_id 4714. This avoided paid/cloud image generation and produced a more photoreal background than procedural buildings.

**Source files**

- projects/CityCharacterPipeline/output/real_photo_plate_video/candidate04_alpha_photo_v4_clean_meta.json
- projects/CityCharacterPipeline/output/real_photo_plate_video/RickDias_real_photo_plate_v4_clean.mp4

## 2026-05-21 02:51:22 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

2026-05-21 CityCharacterPipeline photoreal v5: To improve the v4 real-photo-plate composite, focus on the robot CG mismatch rather than the background. Effective local-only changes: threshold the alpha matte (>96) to remove old procedural background halos, feather 1.05px, use lower-half matte growth only for feet/legs, shift robot down 72px for road contact, add stronger dual contact shadow, use mild local background defocus around the robot silhouette, reduce robot saturation/contrast/brightness (0.82/0.93/0.91), add tiny film grain and restrained vignette. Output: projects/CityCharacterPipeline/output/real_photo_plate_video/RickDias_real_photo_plate_v5_cinema.mp4, Telegram message_id 4716. Source photo remains Pixabay id 5655593 by djedj. No paid/cloud image generation.

**Source files**

- projects/CityCharacterPipeline/output/real_photo_plate_video/candidate04_alpha_photo_v5_cinema_meta.json
- projects/CityCharacterPipeline/output/real_photo_plate_video/RickDias_real_photo_plate_v5_cinema.mp4

## 2026-05-21 04:07:18 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

2026-05-21 CityCharacterPipeline: User rejected 2D photo plate background as unacceptable. Switched back to true 3D background. Attempt v1 added dense procedural 3D street canyon, road, signs, traffic lights, and camera dolly, but legacy OSM geometry produced a black overhang in camera. Attempt v2 hid legacy OSM/enhancement visual meshes and rendered clean 3D city, but background was too box-like and low-detail. Attempt v3 added road-edge storefronts/signs and wider camera for 3D parallax; output RickDias_real_3d_city_v3_storefronts.mp4 sent to Telegram message_id 4717. Result is acceptable only as a 3D direction/evaluation asset, not photoreal final. Next recommended route for final quality: UE5/PLATEAU/Megascans or Blender with real asset packs; procedural boxes alone cannot reach YouTube photoreal city quality.

**Source files**

- projects/CityCharacterPipeline/output/real_3d_city_v3_storefronts/RickDias_real_3d_city_v3_storefronts.mp4
- projects/CityCharacterPipeline/output/real_3d_city_v3_storefronts/blender_scene_script_real_3d_city_v3.py

## 2026-05-21 06:32:22 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

UE5 local no-cloud render baseline: UnrealEditor 5.7.4 at D:\UnrealEngine\UE_5.7\UE_5.7 can run AtsugiMechaCity offscreen with SceneCapture2D and export EXR without AI/cloud API consumption. HighResShot/editor viewport path is unstable/headless and produced sky/black/hangs. SceneCapture2D export_render_target works; UE writes EXR even if extension says PNG. Convert with ffmpeg from .exr to PNG. Existing Atsugi_Front_Final and Zaku_Posed spawn, but city/camera/material scale are unreliable; procedural UE primitives can create true 3D road/building background. Color material generation via /Temp MaterialEditingLibrary failed in UE 5.7 with create_material_expression returning None, so current output falls back to existing gray PBR materials. Next fix: create real Material assets under /Game/CodexGenerated or use confirmed engine material with parameters, then build Movie Render Queue sequence.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_capture2d.py,projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_procedural_city.py,projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_procedural_city_report.json

## 2026-05-21 07:04:49 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

UE5 local procedural city render advanced color pass: fixed material creation by writing reusable assets under /Game/CodexGenerated instead of /Temp. Added v2 saturated asphalt, lane, glass, sky, facade materials plus sidewalk and traffic light emissive materials. Added sidewalks, crosswalk, asphalt detail strips, window cells, red/amber/green traffic lights, and overhead road signs in ue5_render_procedural_city.py. Latest checked PNG is projects/AtsugiMechaCity/diagnostics/ue5_local_render/Atsugi_UE5_procedural_city_color2_view.png. Still not photorealistic; it is a true 3D UE5 stylized/procedural city baseline. Next realistic step: replace primitive blocks with PLATEAU/Megascans/PBR mesh assets or import real city meshes, then render with Movie Render Queue.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_procedural_city.py

## 2026-05-21 07:55:57 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

UE5 local PLATEAU render attempt 2026-05-21: Blender Hon_Atsugi_Station_Plateau_Mecha.blend was exported to UE5 FBX via diagnostics/ue5_local_render/export_hon_atsugi_plateau_for_ue5.py. Key fixes: exclude oversized mecha from city background FBX, recenter city to origin, apply transforms, use global_scale=1. UE5 import/render script diagnostics/ue5_local_render/ue5_import_render_plateau_fbx.py imports to /Game/CodexGenerated/PlateauHonAtsugiCityOnlyCmScale, uses SceneCapture2D, applies material slots for terrain/building/window/sign/road/sidewalk/line/rail/plaza. Output: Atsugi_UE5_plateau_city_real_asset_materialized_view.png. Result: API cost none; real PLATEAU geometry imports successfully, but visual is still blocky/gray and not photoreal because CityGML-derived buildings are simple boxes and lack facade textures/detail; next improvement should add real facade textures/PBR assets or use higher quality UE/Megascans-like assets.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/export_hon_atsugi_plateau_for_ue5.py
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_import_render_plateau_fbx.py

## 2026-05-21 08:02:23 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

Created projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_PLATEAU_RENDER_ANALYSIS.md summarizing the UE5/PLATEAU photoreal background attempt through 2026-05-21. It records: local-only/no API use, procedural UE5 baseline, Blender PLATEAU FBX export, PostProcessVolume UE5.7 property failure and fix, recentering, exclusion of oversized mecha from background FBX, global_scale=1 correction, UE5 material slot reassignment, remaining limitation that PLATEAU box geometry lacks photoreal facade/PBR detail, and recommended next steps: split mesh import, SkyAtmosphere/exposure/fog, PBR material library, decoration assets, then separate mecha integration/video/Telegram.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_PLATEAU_RENDER_ANALYSIS.md

## 2026-05-21 09:27:07 +09:00

**Curate status:** completed

**Reason:** brv curate completed successfully

**Context**

Ingested C:\Users\yasu\Downloads\UE5_MINIPC_VIDEO_ADVICE_20260521.md into projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_MINIPC_VIDEO_GENERATION_ADVICE.md and appended its key guidance to UE5_PLATEAU_RENDER_ANALYSIS.md. Updated guidance: ADOPT_PARTIAL, mini-PC first target is still-image comparison at 1280x720, city-only radius 100m, background/mecha separated, split exports for Terrain/Road/Sidewalk/Buildings/Windows/Signs/Rails/Props, SceneCapture2D/RenderTarget/EXR standard, avoid HighResShot/editor viewport, avoid initial Lumen/Nanite/high-quality shadows, apply PBR in order road/sidewalk/building/window/sign, pass only after black background/bounds/material issues are resolved.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_PLATEAU_RENDER_ANALYSIS.md
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_MINIPC_VIDEO_GENERATION_ADVICE.md

## 2026-05-21 10:03:32 +09:00

**Curate status:** completed

**Reason:** brv curate completed successfully

**Context**

Implemented and ran the UE5 mini-PC safe radius100 still-image comparison flow. Added export_city_split_radius100_for_ue5.py, ue5_render_radius100_comparison.py, config_ue5_minipc_render_profile.json, and radius100_compare_template.md under projects/AtsugiMechaCity/diagnostics/ue5_local_render. Blender split export succeeded for Terrain/Road/RoadMarkings/Sidewalk/Buildings/Windows/Rails; Signs had no faces in the slice. UE5 rendered 1280x720 baseline/pbr_road/pbr_road_building_props via SceneCapture2D and EXR output, converted to PNG, and created r100_contact_sheet.png. Fixed a camera bug: initial camera used terrain min Z and sat below the road layer; now it uses road/sidewalk bounds and a sky backdrop. Result is end-to-end successful and local-only, but not photoreal yet; next still fix should improve camera composition, hide/blocking buildings, strengthen road/sidewalk PBR contrast, and enlarge visible props before video.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/export_city_split_radius100_for_ue5.py
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_radius100_comparison.py
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_PLATEAU_RENDER_ANALYSIS.md

## 2026-05-21 10:13:10 +09:00

**Curate status:** completed

**Reason:** brv curate completed successfully

**Context**

UE5 radius100 composition v2 completed. Backup branch pushed: backup/ue5-radius100-composition-before-20260521-100841. Updated ue5_render_radius100_comparison.py to improve street composition: camera recentered at road surface, PLATEAU Windows actor hidden in final variant to avoid giant blue wall, foreground asphalt proxy enlarged/darkened, lane stripes/crosswalk/curbs added, proxy facades/windows/cars/sign/poles added. Output r100_pbr_road_building_props.png now shows a readable street with road surface, lane markings, facades and props, though still not photoreal. Next still-image loop should add PBR wall/tile textures, emissive traffic lights, TextRender signs, and better low-poly vehicle shapes before video.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_radius100_comparison.py
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/UE5_PLATEAU_RENDER_ANALYSIS.md
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare_template.md

## 2026-05-21 12:12:50 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

UE5 Hon Atsugi cinematic foreground variant: Added cinematic_station_front_set variant for Hon Atsugi UE5 radius100 comparison. Backup branch pushed before changes. NullRHI failed with divide-by-zero in SceneCapture2D; retry without nullrhi succeeded. Added 78 foreground proxy props, report/harness status, and Telegram contact sheet output. Remaining limitation: proxy/blockout quality, not photoreal.

**Source files**

- projects/AtsugiMechaCity/diagnostics/ue5_local_render/ue5_render_radius100_comparison.py
- projects/AtsugiMechaCity/diagnostics/ue5_local_render/radius100_compare/radius100_ue5_compare_report.json

## 2026-05-21 13:07:55 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

Implemented ByteRover fallback automatic resync queue. brv_safe_curate now writes pending JSONL queue entries on timeout/failure, and brv_sync_curate_queue retries pending entries after quota recovery with bounded MaxItems, timeout control, backoff, archive on success, and no data loss on failure.

**Source files**

- scripts/brv_safe_curate.ps1
- scripts/brv_sync_curate_queue.ps1
- docs/INCIDENT_LOG.md

## 2026-05-23 06:19:48 +09:00

**Curate status:** failed

**Reason:** brv curate failed

**Context**

Atsugi Mecha City LOD2 PBR and SD v40 photorealism integration pattern

**Source files**

- .brv/context-tree/design/atsugi-lod2-photoreal-hybrid-pattern.md

## 2026-05-29 23:36:23 +09:00

**Curate status:** timeout

**Reason:** brv curate timed out after 30s

**Context**

GitHub backup method for repo Yasu2019/Clawdbot (2026-05-29). Use dated backup branches named backup/*. CRITICAL: CAE/simulation work lives in GITIGNORED paths - clawstack_v2/data/ (junction, .gitignore line 26) and data/workspace/** (line 74). Plain git add or push will NOT back them up; MUST force-add with 'git add -f PATH'. Steps: (1) force-add work artifacts - two .rad decks, doe_design_next.csv, openradioss_autonomous_status.json; (2) commit with -m message; (3) git push -u origin HEAD when branch has no upstream. Do NOT git add -A - pulls GBs of unrelated large binaries (.exr, PNG frames, .glb, .fbx up to 89MB). GitHub warns at 50MB, rejects over 100MB; consider Git LFS later. Env: PowerShell on Windows - no head/heredoc, avoid angle brackets in shell commands.

**Source files**

- none

