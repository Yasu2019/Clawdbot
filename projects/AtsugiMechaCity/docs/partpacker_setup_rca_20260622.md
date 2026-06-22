# PartPacker Setup RCA 2026-06-22

## Event

PartPacker setup progressed, but full JPEG-to-3D generation could not be executed.

## Current State

- Python 3.10.11 installed by winget.
- Official `NVlabs/PartPacker` cloned to `D:/AI/PartPacker`.
- Virtual environment created at `D:/AI/PartPacker/.venv`.
- Torch `2.5.1+cu124`, torchvision `0.20.1+cu124`, and torchaudio installed.
- `pip install -r requirements.txt` completed after installing `fpsample==0.3.3` binary wheel.
- Import smoke passed for PartPacker runtime dependencies.
- `vae.pt` downloaded to `D:/AI/PartPacker/pretrained/vae.pt`.
- `flow.pt` is not available yet.
- `torch.cuda.is_available()` returns `False`.

## 5 Whys

1. Why could JPEG-to-3D generation not run?
   The required `flow.pt` model is missing and CUDA is unavailable to PyTorch.
2. Why is `flow.pt` missing?
   Hugging Face download reached timeout once, then token/Xet and HTTP retry paths showed no measurable progress.
3. Why did the first requirements install fail?
   `fpsample==1.0.2` tried to build from source and required NMake/C++ compiler.
4. Why did that recover?
   `fpsample==0.3.3` has a Windows cp310 wheel and satisfies the import path used by PartPacker.
5. Why is CUDA unavailable?
   The environment has CUDA torch installed, but PyTorch cannot see a CUDA device; `nvidia-smi` also fails under normal user permission.

## FTA

Top event: PartPacker inference not runnable.

- Model branch: `flow.pt` incomplete.
- GPU branch: `torch.cuda.is_available() == False`.
- Dependency branch: initial `fpsample` build failed, fixed with binary wheel fallback.
- Process branch: Hugging Face download process had to be stopped when progress was not measurable.

## FMEA

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Missing `flow.pt` | No image-to-3D generation | `pretrained/flow.pt` absent | Resume download with token; consider browser/manual download if HF client stalls |
| CUDA unavailable | Inference likely fails or is unusably slow | torch CUDA smoke | Fix NVIDIA driver/permission/GPU access before heavy run |
| `fpsample` source build | Requirements install fails | pip build error, missing `nmake` | Install `fpsample==0.3.3` wheel before requirements |
| HF Xet stalled | No measurable progress | cache size unchanged, target absent | Disable Xet or use manual direct download |

## Web Knowledge Check

Official local README was used after cloning `NVlabs/PartPacker`. It states Windows is confirmed with Python 3.10, CUDA 12.4, Torch 2.5.1, and TorchVision 0.20.1; inference requires about 10GB GPU memory. No further web search changed the countermeasure.

## Countermeasures

- Keep PartPacker as external dependency under `D:/AI/PartPacker`.
- Do not enable generator execution in `jpeg_to_mecha_rig.example.json` until both `flow.pt` and CUDA are verified.
- Use `scripts/download_partpacker_weights.py` for resumable, non-secret-printing weight downloads.
- Keep JPEG-to-rig scaffold usable for inventory/spec tests while generation is blocked.
