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

