# SCAIL-2 / Wan ワークフロー

## 登録済みファイル

`scail2_wan_api.json` — ComfyUIのAPIフォーマット。**ComfyUI 0.26.0 の
`WanSCAILToVideo` 実装（`comfy_extras/nodes_scail.py`）のシグネチャに合わせて作成**し、
稼働中の本番GPUインスタンスに対して構造検証済みです。

**コアノードのみで構成**しています（VideoHelperSuite等のカスタムノードに依存しません）。
本番GPU機にはVHSが入っていないため、動画の読み書きはコアの
`LoadVideo` → `GetVideoComponents` / `CreateVideo` → `SaveVideo` を使います。

```
UNETLoader ─→ ModelSamplingSD3 ─────────────────┐
CLIPLoader(type=wan) ─→ CLIPTextEncode(pos/neg) ┤
VAELoader ──────────────────────────────────────┤
CLIPVisionLoader ─→ CLIPVisionEncode ───────────┤
LoadImage(reference) ───────────────────────────┼→ WanSCAILToVideo ─→ KSampler
LoadVideo → GetVideoComponents(pose_video) ─────┘                        ↓
                                                  VAEDecode → CreateVideo → SaveVideo(mp4/h264)
```

### 0.24 と 0.26 でノード仕様が変わっている

同じ `WanSCAILToVideo` でも版で別物です。古い版向けのJSONは0.26では通りません。

| | 0.24.0 | 0.26.0（本番GPU機） |
|---|---|---|
| 出力 | 3個 | **4個**（`video_frame_offset` 追加） |
| 必須入力 | — | **`video_frame_offset`, `previous_frame_count`** 追加 |
| 任意入力 | — | `pose_video_mask`, `replacement_mode`, `reference_image_mask`, `previous_frames` 追加 |
| 実装場所 | `comfy_extras/nodes_wan.py` | `comfy_extras/nodes_scail.py` |

`previous_frames` / `video_frame_offset` は長尺をチャンク分割して繋ぐためのもので、
前チャンクの出力と `video_frame_offset` を次チャンクへ配線します（SCAIL-2は81フレーム
チャンク・76フレームステップ・アンカー5フレームで学習）。

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
| `REFERENCE_IMAGE` | `example.png` | ComfyUIの `input/` にある**画像名** |
| `POSE_VIDEO` | `pose_reference.mp4` | ComfyUIの `input/` にある**動画名**（パスではない） |
| `WIDTH` / `HEIGHT` / `LENGTH` | `512` / `896` / `81` | 32の倍数 / lengthは4n+1 |
| `POSE_STRENGTH` | `1.0` | ポーズlatentの強さ |
| `SEED` / `STEPS` / `CFG` | `12345` / `20` / `1.0` | サンプラー |
| `FPS` / `FILENAME_PREFIX` | `16.0` / `mecha_studio_scail2` | 出力 |

数値トークンは**数値のまま**置換されます（ComfyUIはINT/FLOAT入力に文字列を渡すと型エラーになるため）。

## 実行前の確認

```
python scripts/run_comfy_workflow.py workflows/scail2/scail2_wan_api.json --preset scail2 --check-only
```

## 現状（2026-08-11 実測 / 本番GPU機 ComfyUI 0.26.0）

```
事前検証: NG（4件）
  - node 1 UNETLoader.unet_name: 'wan2.2_animate_14B_bf16.safetensors' は候補にありません
                                 （在庫: wan2.2_ti2v_5B_fp16.safetensors）
  - node 4 VAELoader.vae_name:   'wan_2.1_vae.safetensors' は候補にありません
                                 （在庫: wan2.2_vae.safetensors, pixel_space）
  - node 5 CLIPVisionLoader:     選択肢が空です（未配置）
  - node 10 LoadVideo.file:      選択肢が空です（input/ に動画なし）
```

在庫にあるモデル名へ差し替えると**残り2件（clip_vision と pose動画）だけ**になり、
16ノードすべての入力名・リンク・0.26の新必須項目が有効であることを確認済みです。

### 在庫のWan2.2 TI2V-5Bでは代用できない

`UNETLoader` に `wan2.2_ti2v_5B_fp16.safetensors` を入れても**動きません**。
`WanSCAILToVideo` は **16チャンネルlatent**を生成しますが
（`nodes_scail.py`: `torch.zeros([batch_size, 16, ...])`、空間1/8）、
TI2V-5Bは `wan2.2_vae` 前提の別アーキテクチャで、チャンネル数が一致しません。

## 不足している資産（4件）

| 資産 | 配置先 | 備考 |
|---|---|---|
| Wan2.2 Animate / SCAIL 系 diffusion model | `models/diffusion_models/` | 在庫のTI2V-5Bでは代用不可 |
| `wan_2.1_vae.safetensors`（16ch） | `models/vae/` | 在庫の `wan2.2_vae`(48ch) では不可 |
| `clip_vision_h.safetensors` | `models/clip_vision/` | ノード上は任意入力だが本ワークフローは使用 |
| ポーズ参照動画 | ComfyUIの `input/` | `LoadVideo` はファイル名で参照する |

モデル保管先は `F:/clawstack_data/comfyui_models`（`extra_model_paths.yaml` 経由）です。
方針としてダウンロード機能は持たせていません。手動配置後に `--check-only` を再実行してください。

## 接続先について

既定の `http://127.0.0.1:8188` は**ネイティブGPU版**（torch 2.8.0+cu128 / cuda:0）です。
Docker CPU版は `18188`（非常用フォールバック）。詳細は
`services/comfyui_fullkit/docs/00_CLAWSTACK_FUSION.md` を参照してください。
