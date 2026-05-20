# CityCharacterPipeline Video Generation Playbook

Date: 2026-05-20 JST
Beads: `iatf_system-ckb`
Incident: `INC-085`
Scope: RickDias/Zaku-style walking movie generation in `projects/CityCharacterPipeline`
Goal: allow a small local LLM, even around 8GB VRAM/RAM class, to reproduce the same level of video without re-discovering the failure modes.

## Golden Baseline

Use the existing pipeline first. Do not create a new renderer, new app, new converter, or new Docker flow for this task.

Reference config:

- `projects/CityCharacterPipeline/configs/shibuya_zaku.yaml`
- FBX: `D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/diagnostics/Normal_Walking_RickDias.fbx`
- Character name: `RickDias_Armature`
- Character height: `20.0`
- Stable timing: `total_frames: 90`, `fps: 30`, `step_length_m: 5.0`
- `action_playback_scale`: omit it or keep it at `1.0`
- Output: `projects/CityCharacterPipeline/output/shibuya_zaku/Shibuya_Zaku_walk.mp4`

Recommended commands:

```powershell
cd D:\Clawdbot_Docker_20260125\projects\CityCharacterPipeline
python run_pipeline.py --config configs/shibuya_zaku.yaml --animate --dry-run
python run_pipeline.py --config configs/shibuya_zaku.yaml --animate --skip-qa
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 output/shibuya_zaku/Shibuya_Zaku_walk.mp4
```

Note: `--dry-run` may still touch pipeline records depending on the current recorder behavior. Treat it as a controlled pipeline check, not a completely inert read-only command.

## Acceptance Gates

The render is not complete until all gates pass:

| Gate | Check | Pass condition |
|---|---|---|
| Python syntax | `python -m py_compile pipeline/scene_builder.py pipeline/material_enhancements.py` | No syntax error |
| Blender render | pipeline log | `ANIMATION RENDER OK` appears |
| Frame hygiene | frame directory | Old `render_frame_*.png` files are removed before the new render |
| MP4 build | pipeline log and file size | `ffmpeg MP4` completes and MP4 size is non-zero |
| Duration | `ffprobe` | About 3.0 sec for 90 frames at 30 fps |
| Texture | Blender/material log or visual frame check | FBX image texture material is preserved, not replaced by plain metal |
| Grounding | pipeline log | `min_foot_z >= 0.05` and `min_clearance >= 0.05` |
| Visibility | visual frame check | feet/lower body are not hidden by OSM building or foreground roof geometry |
| Motion | visual video check | walking is visibly moving, not a near-still image |
| Delivery | Telegram/send step if requested | message id returned and MP4 path matches latest output |

## Critical Implementation Points

1. Preserve FBX textures.
   - `material_enhancements._apply_metal_pbr()` must not overwrite existing image texture materials.
   - If an imported material has image nodes, adjust only roughness/metallic values and keep the texture graph.

2. Remove stale frames before ffmpeg.
   - `_render_animation()` must delete old files matching the frame prefix before starting Blender render.
   - Without cleanup, ffmpeg can pick leftover frames from an older longer render and create the wrong duration.

3. Treat burial as both geometry and visibility.
   - Positive foot Z is necessary but not sufficient.
   - Hide OSM buildings in both the walking corridor and the camera sight corridor when they visually cover the lower body.

4. Support Blender 5.x action data.
   - Imported Mixamo/FBX actions may use Layered Action `channelbags`.
   - Transform curve cleanup must handle both old `Action.fcurves` and Blender 5.x structures.

5. Keep the successful motion baseline.
   - The 5 sec slow version looked like a still image.
   - Restore `90` frames, `step_length_m=5.0`, and `action_playback_scale=1.0` unless a new visual motion gate is added.

6. Keep Windows output encoding safe.
   - Python files edited in this repo need the stdout UTF-8 reconfigure snippet at module top.
   - Avoid non-cp932 symbols in `print()` messages.

## QC Process Chart / PMP

| # | Process | Input | Control method | Pass criteria | Record |
|---|---|---|---|---|---|
| 1 | Request capture | User visual goal | Confirm target asset, scene, delivery channel | Goal is one movie, not a new platform | Beads issue |
| 2 | Config selection | `shibuya_zaku.yaml` | Prefer known-good baseline | 90f, 30fps, 5.0m stride | Playbook/config diff |
| 3 | Asset intake | FBX and reference image | Check FBX imports with materials | Image texture material exists | Render log/frame check |
| 4 | Material preservation | Imported materials | Preserve texture nodes | No plain grey/white replacement | `material_enhancements.py` behavior |
| 5 | Terrain and city scene | OSM/ground assets | Ground and occluder diagnostics | walk/camera corridor clear | Blender log |
| 6 | Animation bake | FBX action | Remove object transform drift, keep armature motion | Character remains in camera | Blender log and frames |
| 7 | Grounding | Per-frame bbox | Compare feet to terrain surface | positive clearance | grounding summary |
| 8 | Render frames | Blender background | Clean frame folder first | exact expected frame count | frame directory |
| 9 | Encode MP4 | ffmpeg | Use current frames only | correct duration, non-zero file | MP4 and ffprobe |
| 10 | Visual QA | sample frames/movie | Human-visible texture, feet, motion | not buried, textured, moving | notes or Telegram |
| 11 | Delivery | Telegram if requested | Send only after latest MP4 is verified | message id returned | Telegram result |
| 12 | Knowledge capture | docs, Beads, ByteRover | Record failure modes and gates | future agent can reproduce | this playbook |

## FMEA

| Failure mode | Effect | Cause | Severity | Occurrence | Detection | RPN | Control |
|---|---|---|---:|---:|---:|---:|---|
| FBX texture overwritten | Robot appears untextured | generic PBR material replaces imported image nodes | 8 | 4 | 4 | 128 | Preserve existing image materials by default |
| Stale frames encoded | duration or motion does not match current render | old frames remain after shorter render | 7 | 5 | 3 | 105 | Delete frame prefix before render, verify frame count |
| Motion looks static | video feels like still image | too much slowing, too little screen displacement | 7 | 4 | 5 | 140 | Keep 90f/5.0m baseline, visual motion gate |
| Lower body looks buried | failed review/presentation | OSM building or roof occludes feet | 9 | 4 | 4 | 144 | clear walk and camera corridor occluders |
| Feet actually below terrain | obvious physical error | insufficient per-frame lift | 9 | 3 | 3 | 81 | per-frame surface clearance and min foot Z logs |
| Character leaves camera | black/empty or poor framing | FBX root/object location curves | 8 | 3 | 4 | 96 | remove object transform curves and check camera frame |
| Blender 5.x action cleanup fails | render aborts | code assumes old `Action.fcurves` only | 8 | 3 | 3 | 72 | support Layered Action `channelbags` |
| Telegram sends old movie | wrong artifact delivered | send step uses stale path or old MP4 | 6 | 3 | 4 | 72 | verify timestamp, size, and latest render log |
| Local LLM over-refactors | new bugs appear | small model changes too much code | 8 | 4 | 6 | 192 | config-first, narrow patches, no new renderer |

## FTA

Top event: reviewable walking 3D robot movie is not generated.

- Asset branch
  - FBX missing or wrong armature name
  - Embedded textures overwritten
  - Reference image used as expectation but not converted into material check
- Motion branch
  - Action object/root transforms move character away
  - Slow settings reduce apparent motion too much
  - Blender 5.x action API mismatch prevents cleanup
- Scene branch
  - Terrain contact is checked only against z=0
  - OSM foreground geometry hides the legs
  - Camera sight corridor is not cleared
- Render/output branch
  - Old frame files remain
  - ffmpeg consumes more frames than the current render
  - MP4 is delivered before duration/size checks
- Process/memory branch
  - Lessons are scattered across logs
  - No QC/FMEA/FTA checklist is available to the next agent
  - Local LLM changes implementation before preserving the known-good baseline

## Five Why

### Why did the slow version look stopped?

1. It looked stopped because visible screen-space movement became too small.
2. Movement became too small because frame count was increased while stride was reduced and action playback was slowed.
3. Those changes were made to make the robot feel massive, but there was no separate visual motion gate.
4. The pipeline optimized "slower" without checking whether the output still read as walking.
5. The standard must preserve the successful baseline first, then adjust speed only with visual verification.

Countermeasure: keep `90` frames, `5.0m` stride, and playback scale `1.0` as the baseline.

### Why did the robot appear to have no texture?

1. The robot looked untextured because the imported FBX image material was not visible.
2. The material became plain because the pipeline applied a generic metal PBR material.
3. The material enhancement step did not distinguish "missing material" from "existing textured material".
4. There was no gate that checked imported image texture nodes before overriding.
5. The process treated material enhancement as always safe.

Countermeasure: preserve existing image texture nodes and only use fallback PBR when no texture exists.

### Why did the robot look buried?

1. The lower body looked buried in the rendered movie.
2. The feet were not below ground; OSM foreground geometry hid the lower body.
3. The old check focused on foot Z and initial origin, not the full walk/camera corridor.
4. The camera view was not treated as a collision/visibility path.
5. The pipeline lacked a combined grounding plus occlusion acceptance gate.

Countermeasure: keep per-frame clearance logs and hide OSM occluders in walk and camera corridors.

### Why did output duration become wrong after changing frame count?

1. ffmpeg encoded extra frames.
2. Extra old PNG frames remained in the frame directory.
3. The render step did not clean old files before shorter renders.
4. The encode step trusted a filename pattern instead of an exact new frame list.
5. Frame hygiene was not an explicit gate.

Countermeasure: delete old frame-prefix PNGs before each render and verify exact frame count.

## Fishbone

| Category | Causes | Controls |
|---|---|---|
| Agent | over-refactor, too many hypotheses at once, no visual gate | config-first, one hypothesis per run, use this checklist |
| Tools | Blender 5.x action API, ffmpeg image pattern, Windows cp932 stdout | support channelbags, clean frames, UTF-8 stdout |
| Assets | FBX packed textures, armature naming, Mixamo root curves | inspect imported materials, fixed `RickDias_Armature`, strip object transforms |
| Method | material override, z-only grounding, no frame cleanup | preserve textures, corridor occlusion check, frame hygiene |
| Measurement | dry-run not enough, no duration check, subjective motion | ffprobe, frame count, sample frame and movie review |
| Environment | Windows paths, CPU render time, Telegram delivery | absolute paths, bounded commands, verify message id |

## Local LLM 8GB Operating Rules

- Read this playbook and the current config before editing.
- Prefer changing YAML/config before Python code.
- Change one variable per run: texture, grounding, motion speed, camera, or output hygiene.
- Keep patches small and local to the existing pipeline.
- Do not introduce a new app, renderer, Docker service, or workflow for this movie.
- Do not replace the successful 90-frame timing unless a visual motion check is planned.
- Use deterministic logs and file checks before subjective judgement.
- If the movie looks wrong but logs look right, suspect camera occlusion or stale frames before changing physics.
- Record every final fix in `docs/INCIDENT_LOG.md`, Beads, and ByteRover if available.

## No-Go Conditions

Hold the change and ask for review if any of these are required:

- modifying Docker Compose or core infrastructure
- replacing Blender/ffmpeg with a new rendering stack
- adding a new dashboard or app just for this movie
- mass reformatting pipeline files
- deleting unrelated generated assets
- auto-sending externally before the latest MP4 is verified

## Final Checklist

- [ ] Config matches the golden baseline or the diff is intentional.
- [ ] Existing FBX texture nodes are preserved.
- [ ] Walk and camera corridor occluder checks are enabled.
- [ ] Old frame files are cleaned before render.
- [ ] MP4 duration and size match the latest run.
- [ ] Visual review confirms texture, feet visibility, and walking motion.
- [ ] Telegram send, if requested, uses the latest MP4.
- [ ] Incident log, Beads, and ByteRover/local knowledge are updated.
