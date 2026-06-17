# Handover: Mecha Auto-Rig → Walking Video + PartCrafter Part-3D Pipeline (2026-06-17)

**For:** the next agent (Gemini / GPT-5.5). This is self-contained — you should not need the prior chat.
**Author:** Claude (Opus 4.8) session `feat/mecha-autorig`.
**Repo root:** `D:\Clawdbot_Docker_20260125` (Windows; Git Bash available; PowerShell default).

---

## 0. North-Star Goal
User wants an **18 m mecha (Zaku-style) that walks naturally**, rendered as a vertical video, on a PLATEAU/factory background. The walk must be genuinely correct (no false-PASS): legs bend at hip/knee/ankle, joints do NOT separate, arms not stuck in a T-pose.

Two halves:
1. **Rigging engine** (DONE, reusable) — turn a part-separated mecha mesh into a rig that walks without joint gaps.
2. **Getting a well-segmented mecha model** (IN PROGRESS) — the original MeshyAI Zaku has terrible segmentation; we are generating a better one with **PartCrafter** (image → part-separated 3D).

---

## 1. What is DONE and committed (branch `feat/mecha-autorig`, pushed to GitHub `Yasu2019/Clawdbot`)

### 1a. Joint-integrity rig rules ①〜④ (in `projects/AtsugiMechaCity/mecha_rig_builder.py`)
The auto-rig had NO rule keeping a joint's two parts connected → arms detached, thighs split. Implemented:
- **① pivot = real joint center**: `snap_bones_to_joint_centers()` — moves each bone HEAD to the geometry-derived joint center (midpoint of closest contact between child & parent segment meshes), instead of hardcoded bounding-box proportions. Translate-only so local axes stay valid. Only snaps when the IMMEDIATE parent bone has geometry.
- **② joint cores**: `add_joint_cores()` — sphere primitives at each pivot, bound to the CHILD bone, to physically fill the rigid-hinge gap. **Finding: cores fill INTERNAL joint gaps but cannot reach OUTER armor seams; oversizing = ugly balls.**
- **③ limit range**: (LIMIT_ROTATION already present; not the bottleneck).
- **④ separation QC gate**: `projects/AtsugiMechaCity/qc_joint_separation.py` — **CRITICAL & FIXED**. The original measured "min closest distance" → a rigid hinge keeps one edge touching while the opposite edge opens a visible gap → it false-PASSED twice (arm, thigh). **Now measures CONTACT-PATCH OPENING**: record the child verts touching the parent at rest, then measure their MAX separation across a ±20° sweep (+ a rest static-gap check). tol = 2.2% of model height. Run: `blender --background --python projects/AtsugiMechaCity/qc_joint_separation.py -- --blend <file.blend>`.

### 1b. Other rig tools (all in `projects/AtsugiMechaCity/`)
- `qc_multiview.py` — renders **front/side/back at sampled frames** (QC rule: sample every 5 frames, never approve on one hero frame).
- `apply_rule1_pivot_snap.py`, `apply_rig_fixes_v4.py`, `apply_joint_cores_v6.py`, `apply_mirror_left_arm_v7.py`, `resegment_left_arm_v5.py` — post-hoc appliers that upgrade an existing `.blend` (v2→v3→…→v6) without a full FBX rebuild.
- `scenes/zaku_walk_origin_style.py` — the walk animation + render. World-space forward translation on `armature.location` (NOT pose-bone, which sinks the model). Numerical `--verify` gate (forward travel, grounded, alternate, arm swing). Full-body side camera. `aim_bone_world()` = axis-agnostic world-space arm aiming.

### 1c. Lessons recorded
- `data/workspace/memory/trouble_history.md`: **T031** (false-PASS broken Zaku), **T032** (sink bug + hip gap), **T033** (no joint-separation rule), **T035** (④ gate min-distance false-PASS → contact-patch fix).
- `bd` memories: `mecha-rig-joint-integrity-t033`, `qc4-gate-visible-gap-fix-t035`, `partcrafter-mecha-pipeline-kaggle`. (`bd recall <key>`.)
- Turso `growth_records` (domain `mecha_rigging_3dgen`). 
- Memory file `reference_mecha_rigging_best_practices.md` updated with the ①〜④ gap.

### 1d. The MeshyAI Zaku verdict (why we moved on)
`D:/Temp/Zaku_AutoRig_v2.blend` (+ v3/v4/v5/v6 derived). 50 rigid segments. After ①〜④:
- ✅ Legs walk (hip ±11°, knee ~22°, ankle ~12°, alternating), joint **separation** within tolerance.
- ❌ **Left arm**: one merged segment `part_10` sits above its pivot → contorts when posed (exhausted ① / re-seg / world-aim / mirror / euler). Gave up (arms at rest).
- ❌ **Thigh armor outer seam** opens during the swing (rigid segments, no overlap) — cores can't reach it.
**Root cause = poor source segmentation, not the rig.** Hence PartCrafter.

---

## 2. CURRENT TASK: PartCrafter → part-separated mecha GLB (IN PROGRESS)

### 2a. Why PartCrafter
PartCrafter (github.com/wgsxm/PartCrafter, NeurIPS 2025, MIT) generates a 3D mesh **decomposed into semantic parts from one RGB image**. Better segmentation than MeshyAI → should rig cleanly with ①〜④.
- It is STATIC decomposition only — **no functional joints**; we still rig it.
- **User's idea to implement once we have parts:** if PartCrafter emits a joint-shaped part, rig it as an **axis bone with BALL constraints at both ends** (DAMPED_TRACK / Stretch-To to the two attachment points) = a connecting-rod linkage that flexes gap-free. See `reference_mecha_rigging_best_practices.md`.
- **Plan B if PartCrafter parts have gaps:** `github.com/FishWoWater/Part3DGen` (wraps Hunyuan3D-2 + PartField + **HoloPart part-completion** + TRELLIS). HoloPart completes each part into a watertight solid → parts overlap → no gaps. Heavier install (~15 GB VRAM, conda, submodules).
- `PartGen` (Meta+Oxford, arxiv 2412.18608) is technically great (contextual completion of hidden parts) but **NOT usable** — no public code/weights, trained on licensed data.

### 2b. Source image (DONE)
Generated locally with SD: container `ai_image_gen-ai_image_gen-1` on **port 8101** (SDXL-Lightning-2steps OpenVINO, CPU — SLOW, ~13 min at 8 steps; use 2 steps). API: `POST http://127.0.0.1:8101/generate {"prompt","negative_prompt","steps","guidance_scale"}`. Output saved in container `/app/outputs/<id>.png`; pull with `docker cp`.
Final input image (front-view mecha, plain bg, arms at sides): **`projects/AtsugiMechaCity/partcrafter/mecha_src.png`** (1024²). A 768² JPEG is embedded (base64) inside the Kaggle notebook so no upload is needed.

### 2c. Execution path THAT WORKS: Kaggle CLI headless (NOT the browser)
Free Colab/Kaggle **browser** sessions kept idle-resetting (lost the ~15-min install repeatedly) and HF Spaces are all down (theYiran GPU-error, alexnasa PAUSED, paulpanwang/amiedd BUILD_ERROR). **Solution = run on Kaggle servers via the CLI, headless.**

**Auth (already configured):**
- Kaggle access token (KGAT) is in `.env` as `Kaggle_API=KGAT_...`. It was written to `C:\Users\yasu\.kaggle\access_token` (the CLI 2.2.1 reads this automatically). The old `kaggle.json` had the wrong username (email) → renamed to `kaggle.json.bak`.
- Kaggle username/handle: **`yasuhirosuzuki2021`**. Kernel slug: **`yasuhirosuzuki2021/partcrafter-mecha`**.
- `kaggle` CLI is NOT on PATH → call **`python -m kaggle`**. ALWAYS prefix `export PYTHONUTF8=1` (Windows cp932 vs UTF-8 notebook → push fails otherwise).

**The notebook & how it's built:**
- Generator: `D:/Temp/build_kaggle_nb2.py` (committed copy: `projects/AtsugiMechaCity/partcrafter/build_kaggle_nb.py`). Edit cells there, re-run it, it writes `data/workspace/partcrafter/PartCrafter_Kaggle.ipynb` and validates syntax. **Use list-of-lines cell sources (it does) to avoid the `\n`-in-string bug.**
- Kernel push folder: `D:/Temp/kaggle_kernel/` (has `PartCrafter_Kaggle.ipynb` + `kernel-metadata.json` with `enable_gpu:true, enable_internet:true`).
- Notebook cells: (1) nvidia-smi, (2) install, (2b) import check, (3) decode embedded image, (4) inference, (5) collect GLB + STATUS.
- **Install fixes baked in (all required):** pin `torch==2.5.1 torchvision==0.20.1 --index-url .../cu124` BEFORE setup.sh; `bash settings/setup.sh`; `pip install "transformers<5" "diffusers==0.38.0"` (do NOT pin huggingface_hub/tokenizers — diffusers 0.38 needs hub>=0.34, over-pinning → ResolutionImpossible); **rebuild torch_cluster FROM SOURCE** (`pip install --no-cache-dir --no-build-isolation torch-cluster` with `CUDA_HOME=/usr/local/cuda FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST=7.5`) — the prebuilt wheel ABI-mismatches (undefined symbol). Import check prints `IMPORTS OK | torch 2.5.1+cu124 | transformers 4.57.x | diffusers 0.38.0 | cuda True` — **this PASSES (deps fully resolved).**

**Commands to drive it:**
```bash
cd /d/Clawdbot_Docker_20260125 && export PYTHONUTF8=1
# push (uploads + runs on Kaggle servers):
python -m kaggle kernels push -p D:/Temp/kaggle_kernel
# poll:
python -m kaggle kernels status yasuhirosuzuki2021/partcrafter-mecha
# download outputs (note: ~668 MB incl. weights):
python -m kaggle kernels output yasuhirosuzuki2021/partcrafter-mecha -p D:/Temp/kaggle_out
```

### 2d. THE BLOCKER you must solve
The kernel reaches `COMPLETE`, deps import OK, cell 3 writes the image — **but cell 4 (inference) produces NO GLB and `results/` is empty.** Why we couldn't see the error: **Kaggle's `kernels output` only downloads files under the `PartCrafter/` subfolder — NOT files at `/kaggle/working/` root.** (Also the pulled `.ipynb` has no cell outputs.)
- **v4 (currently running as of this handover)** writes the inference log to **`/kaggle/working/PartCrafter/inference_log.txt`** and a **`PartCrafter/STATUS.txt`** (inside the downloadable subfolder) with cell-4 STDOUT/STDERR/exit-code, `ls /kaggle/working`, and `results/` listing.
- **Your first step:** poll v4 → when COMPLETE, `kaggle kernels output` → read `D:/Temp/kaggle_out*/PartCrafter/inference_log.txt` and `STATUS.txt`. That contains the real cell-4 failure (likely CUDA OOM on T4, an arg error, or a wrong output path). Then fix cell 4 in `build_kaggle_nb2.py`, rebuild, re-push.
  - Common fixes: lower `NUM_PARTS` (currently 4) / `--num_tokens` (768); check the actual output dir the script uses (`results/` assumption may be wrong — STATUS.txt's `ls` will show where it wrote); RMBG/background handling.
- Inference CLI (per repo): `python scripts/inference_partcrafter.py --image_path <img> --num_parts N --tag mecha --render` run with `PYTHONPATH=/kaggle/working/PartCrafter`.

### 2e. After you get `mecha_parts.glb`
1. Load into Blender, run the **④ gate** (`qc_joint_separation.py`) + `qc_multiview.py` (front/side/back) to judge: are parts clean, do they overlap (no gaps)?
2. If good → rig with ①〜④ (+ the axis/ball-both-ends linkage for any joint parts), animate with `scenes/zaku_walk_origin_style.py` (adapt bone names), render the vertical walk video.
3. If parts have gaps → switch to **Part3DGen** (Plan B, HoloPart completion).
4. Deliver MP4; user likes the ORIGIN-style framing but a full-body side camera shows the walk best. Telegram send script: `data/workspace/send_video_telegram.py` (reads token from `.env`).

---

## 3. Backups status (requested by user)
- **GitHub**: ✅ pushed (commit `254a4d7d` + rig commits). PartCrafter pipeline under `projects/AtsugiMechaCity/partcrafter/`.
- **Beads**: ✅ memories recorded; `.beads/` is git-tracked (no native dolt remote configured).
- **Turso**: ✅ `growth_records` row inserted (libsql_client; creds in `.env`).
- **ByteRover**: ❌ no MCP tool available this session — NOT backed up. Do it if you have the tool.

## 4. Constraints / gotchas (from CLAUDE.md + this session)
- Docker builds: ALWAYS use cache; never `--no-cache` without prior explanation.
- `clawstack_v2/data` is a Junction Point — verify before deleting.
- `.env` is gitignored (keep it so). It contains plaintext secrets (Kaggle pw/API, HF_TOKEN, Turso) — **never print or commit them**; recommend the user move to a secret manager.
- Quality Analysis Protocol (QC工程表/FMEA/FTA) expected before big changes.
- Disk D: filled to 100% once during rendering — `D:\Temp\DiagOutputDir` etc. are safe to clear.
- **Discipline (T031/T035): never claim success on numbers/“COMPLETE” alone — verify the actual artifact (visual + the right metric).** Min-distance/closest-point metrics hide visible gaps.

## 5. Key file map
| Path | What |
|---|---|
| `projects/AtsugiMechaCity/mecha_rig_builder.py` | ①②③ rig rules |
| `projects/AtsugiMechaCity/qc_joint_separation.py` | ④ separation gate (contact-patch) |
| `projects/AtsugiMechaCity/qc_multiview.py` | front/side/back QC render |
| `projects/AtsugiMechaCity/scenes/zaku_walk_origin_style.py` | walk anim + render + --verify |
| `projects/AtsugiMechaCity/partcrafter/` | PartCrafter notebooks + API runner + source image + builder |
| `D:/Temp/build_kaggle_nb2.py` | live Kaggle notebook generator (edit here) |
| `D:/Temp/kaggle_kernel/` | kaggle push folder |
| `data/workspace/memory/trouble_history.md` | T031–T035 lessons |
| `data/workspace/send_video_telegram.py` | Telegram MP4 sender |
| `C:\Users\yasu\.kaggle\access_token` | Kaggle KGAT auth (already set) |

**Immediate next action:** poll `yasuhirosuzuki2021/partcrafter-mecha`; on COMPLETE, download and read `PartCrafter/inference_log.txt` + `STATUS.txt`; that reveals the cell-4 failure → fix → re-push.
