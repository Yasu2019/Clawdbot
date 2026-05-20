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

