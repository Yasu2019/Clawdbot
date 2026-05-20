# CityCharacterPipeline Photoreal Standard

Date: 2026-05-20 JST

## Goal

Standardize the local path for photo-like stills and YouTube-oriented videos without replacing the existing stable preview pipeline.

## Standard Command Set

Fast preview:

```powershell
cd D:\Clawdbot_Docker_20260125\projects\CityCharacterPipeline
python run_pipeline.py --config configs/photoreal_video.yaml --animate --render-profile preview --camera-angle street_low --skip-qa
```

Higher quality video:

```powershell
cd D:\Clawdbot_Docker_20260125\projects\CityCharacterPipeline
python run_pipeline.py --config configs/photoreal_video.yaml --animate --render-profile photoreal --camera-angle street_low --skip-qa
```

Photoreal still with two-pass SD background finishing:

```powershell
cd D:\Clawdbot_Docker_20260125\projects\CityCharacterPipeline
python run_pipeline.py --config configs/photoreal_video.yaml --render-profile photoreal --camera-angle hero
```

## Camera Presets

| Preset | Use |
|---|---|
| `config` | Use the YAML camera exactly as written |
| `hero` | Balanced full-body hero framing |
| `street_low` | More photographic low street-level view |
| `telephoto` | Compressed cinematic perspective |
| `orbit` | Camera orbit for model/scene showcase video |

## Render Profiles

| Profile | Use | Notes |
|---|---|---|
| `preview` | Fast review | 854x480 Eevee for animation |
| `standard` | Medium quality | 1280x720 animation, moderate lighting |
| `photoreal` | Final candidate | Cycles, 1920x1080 animation, stronger light/AO/material gates |

## Quality Rule

Use Blender for geometry, grounding, camera, and motion. Use Stable Diffusion only as finishing, not as the source of truth.

For still images, keep `two_pass: true` so the background can be made more photo-like while the robot stays from the Blender render. For animation, `photoreal` currently prioritizes consistent geometry and motion over SD frame-by-frame finishing, because frame-wise img2img can flicker unless a temporal workflow is added.

## Completion Criteria

- MP4 exists and has non-zero size.
- `ffprobe` duration matches `total_frames / fps`.
- Robot texture is preserved.
- Feet are visible and grounded.
- Motion is visible, not a still-looking slow pan.
- Latest GitHub CI is green after code changes.

## Verified Output

Preview video generated on 2026-05-20:

`D:\Clawdbot_Docker_20260125\projects\CityCharacterPipeline\output\photoreal_video\Shibuya_RickDias_Photoreal_walk.mp4`

`ffprobe` result: H.264, 854x480, 90 frames, 3.000 seconds.
