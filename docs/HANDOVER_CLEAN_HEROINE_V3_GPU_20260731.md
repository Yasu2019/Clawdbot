# CleanHeroineV3 Unity GPU validation handover

- Date: 2026-07-31 JST
- Beads: `Clawdbot_Docker_20260125-hc0l`
- Retry: 18/50 (user-authorized retry window)
- Unity: 6000.0.73f1
- GPU/API: NVIDIA GeForce RTX 5060 Ti / Direct3D11
- Observed GPU load: peak 5%, VRAM peak 108 MiB
- Result: PASS; hand maximum rotation 24.39 degrees

## Visual review

The full body remained in frame. Separated limbs and skirt stayed intact;
metallic shading, three-point lighting, ground contact shadow, and the mid-motion
arm pose were visible. Quality classification remains clean stylized/toy-like,
not photorealistic.

| Artifact | Full path |
|---|---|
| Original handover | `D:\Clawdbot_Docker_20260125\docs\HANDOVER_3D_HEROINE_20260730.md` |
| Blender | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_rigged.blend` |
| FBX | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_rigged.fbx` |
| Motion MP4 | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_motion.mp4` |
| Unity Prefab | `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Characters\CleanHeroineV3\CleanHeroineV3.prefab` |
| Animator Controller | `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Characters\CleanHeroineV3\CleanHeroineV3.controller` |
| Validation scene | `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Characters\CleanHeroineV3\CleanHeroineV3GpuValidation.unity` |
| Windows GPU Player | `F:\UnityBuilds\CleanHeroineV3\CleanHeroineV3.exe` |
| GPU evidence JSON | `D:\Clawdbot_Docker_20260125\harness_status_clean_heroine_v3_gpu_retry18.json` |
| Start frame | `D:\Clawdbot_Docker_20260125\unity_capture_clean_heroine_v3_retry18\frame_start.png` |
| Mid frame | `D:\Clawdbot_Docker_20260125\unity_capture_clean_heroine_v3_retry18\frame_mid.png` |
| End frame | `D:\Clawdbot_Docker_20260125\unity_capture_clean_heroine_v3_retry18\frame_end.png` |

The three scheduled autonomous motion tasks remain Disabled. No legacy v23
Prefab, Controller, scene, manifest, or Build Settings entry was modified.

