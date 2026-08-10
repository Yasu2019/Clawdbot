# SCAIL-2 / Wan ワークフロー

## 登録済みファイル

`scail2_wan_api.json` — ComfyUIのAPIフォーマット。稼働中ComfyUI（0.24.0）の
`WanSCAILToVideo` ノードの**実シグネチャに合わせて作成・構造検証済み**です。

グラフ構成:

```
UNETLoader ─→ ModelSamplingSD3 ─────────────────┐
CLIPLoader(type=wan) ─→ CLIPTextEncode(pos/neg) ┤
VAELoader ──────────────────────────────────────┤
CLIPVisionLoader ─→ CLIPVisionEncode ───────────┤
LoadImage(reference) ───────────────────────────┼→ WanSCAILToVideo ─→ KSampler
VHS_LoadVideoPath(pose_video) ──────────────────┘                        ↓
                                                        VAEDecode → VHS_VideoCombine(mp4)
```

`WanSCAILToVideo` は reference_image を latent 化して `reference_latents` に、
pose_video を半解像度で latent 化して `pose_video_latent` に載せ、
`pose_start`〜`pose_end` の時間範囲だけポーズ条件を効かせます。

## トークン一覧（19個）

| トークン | 既定値（`--preset scail2`） | 用途 |
|---|---|---|
| `DIFFUSION_MODEL` | `wan2.2_animate_14B_bf16.safetensors` | `models/diffusion_models/` |
| `WEIGHT_DTYPE` | `default` | `default` / `fp8_e4m3fn` 等 |
| `SHIFT` | `8.0` | ModelSamplingSD3 |
| `TEXT_ENCODER` | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models/text_encoders/` |
| `VAE_MODEL` | `wan_2.1_vae.safetensors` | `models/vae/` |
| `CLIP_VISION_MODEL` | `clip_vision_h.safetensors` | `models/clip_vision/` |
| `POSITIVE_PROMPT` / `NEGATIVE_PROMPT` | — | プロンプト |
| `REFERENCE_IMAGE` | `rickdias_walk_frame_0001.png` | ComfyUIの `input/` にある画像名 |
| `POSE_VIDEO_PATH` | `/comfyui/input/pose_reference.mp4` | **ComfyUIプロセスから見たパス**（Docker内パス） |
| `WIDTH` / `HEIGHT` / `LENGTH` | `512` / `896` / `81` | 32の倍数 / lengthは4n+1 |
| `POSE_STRENGTH` | `1.0` | ポーズlatentの強さ |
| `SEED` / `STEPS` / `CFG` | `12345` / `20` / `1.0` | サンプラー |
| `FPS` / `FILENAME_PREFIX` | `16.0` / `mecha_studio_scail2` | 出力 |

数値トークンは**数値のまま**置換されます（ComfyUIはINT/FLOAT入力に文字列を渡すと型エラーになるため）。

## 実行前の確認

```
python scripts/run_comfy_workflow.py workflows/scail2/scail2_wan_api.json --preset scail2 --check-only
```

稼働中ComfyUIの `/object_info` と突合し、**投入前に**不足モデルを特定します。

## 現状（2026-08-11 実測）

接続先ComfyUI `127.0.0.1:8188` での事前検証結果:

```
事前検証: NG（4件）
  - node 1 UNETLoader.unet_name: 選択肢が空です（モデル未配置）
  - node 3 CLIPLoader.clip_name: 選択肢が空です（モデル未配置）
  - node 4 VAELoader.vae_name: 候補は ['pixel_space'] のみ
  - node 5 CLIPVisionLoader.clip_name: 選択肢が空です（モデル未配置）
```

グラフ構造・ノード名・入力名・リンクはすべて有効で、**不足しているのは重みファイルのみ**です。
また、このComfyUIは `--cpu` 起動（`torch 2.12.0+cpu`）のため、重みを入れてもWan 14Bの
実用的な生成はできません。GPU有効化が別途必要です。

## 重みの入手

方針としてダウンロード機能は意図的に持たせていません。Comfy-Org配布の
Wan 2.2 Animate 一式（diffusion_models / text_encoders / vae / clip_vision）を手動で取得し、
接続先ComfyUIの各 `models/` 配下へ配置してから `--check-only` を再実行してください。
配置後は `--check-only` が「OK」になり、そのまま `--wait` で実行できます。
