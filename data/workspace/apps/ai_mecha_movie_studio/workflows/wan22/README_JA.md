# Wan2.2 ワークフロー

## 登録済みファイル

`wan22_ti2v_5b_t2v_api.json` — Wan2.2 TI2V-5B によるテキスト→動画（T2V）。
`services/comfyui_fullkit/workflows/wan22_t2v_api.json`（先行実装）をトークン化したもので、
ノードIDも追跡できるよう先行実装に合わせてあります。

**本番GPU機（8188）で今すぐ実行できる唯一の動画ルート**です。必要な重み3点はすべて配置済み。

```
UNETLoader ─→ ModelSamplingSD3 ─────────────┐
CLIPLoader(type=wan) ─→ CLIPTextEncode(±) ──┤
VAELoader ─→ Wan22ImageToVideoLatent ───────┼→ KSampler → VAEDecode
                                                          ↓
                                            CreateVideo → SaveVideo(mp4)
```

`Wan22ImageToVideoLatent` に `start_image` を渡していないので純粋なT2Vです。
I2Vにする場合は `LoadImage` を足して `start_image` へ配線します。

## トークン一覧（17個）

| トークン | 既定値（`--preset wan22_t2v`） |
|---|---|
| `DIFFUSION_MODEL` | `wan2.2_ti2v_5B_fp16.safetensors` |
| `WEIGHT_DTYPE` / `SHIFT` | `default` / `8.0` |
| `TEXT_ENCODER` | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` |
| `VAE_MODEL` | `wan2.2_vae.safetensors` |
| `POSITIVE_PROMPT` / `NEGATIVE_PROMPT` | 精密部品のターンテーブル撮影 |
| `WIDTH` / `HEIGHT` / `LENGTH` | `640` / `384` / `81`（lengthは4n+1） |
| `SEED` / `STEPS` / `CFG` | `20260806` / `20` / `5.0` |
| `SAMPLER` / `SCHEDULER` | `uni_pc` / `simple` |
| `FPS` / `FILENAME_PREFIX` | `24.0` / `video/mecha_studio_wan22` |

## 実行

```
python scripts/run_comfy_workflow.py workflows/wan22/wan22_ti2v_5b_t2v_api.json \
    --preset wan22_t2v --wait --dest workspace/sample_mecha_movie/output/wan22
```

VRAM不足時は **解像度 → フレーム数 → steps** の順に下げます
（`services/comfyui_fullkit/docs/02_RTX5060Ti推奨設定.md`）。

## 実測（2026-08-11 / RTX 5060 Ti 16GB / ComfyUI 0.26.0 GPU版）

| 設定 | 所要 | 出力 |
|---|---|---|
| 640x384 / 33frames / 20steps（初回・モデルロード込み） | 220秒 | 52 KB mp4 |
| 640x384 / **81frames** / 20steps（ウォーム） | **79秒** | 134 KB mp4 (h264 / 24fps / 3.4秒) |

初回の220秒はほぼモデルロード時間です。連続実行ならウォーム値が実効値になります。

**目視確認**: 81フレーム版はフレーム0/20/40/60/80を抽出して確認済み。
被写体（加工部品）は3.4秒を通して形状破綻なく、背景が連続的にパンする。
`scene_score` は 0.003〜0.034 で推移し、不連続なカットやフリッカーは無し。
33フレーム版は動きがほとんど出なかったため、**尺は81フレームを既定とすること**。

## GPU調停

長時間の生成前に、他ジョブ（RL学習・CAE）とのVRAM競合をリースで調停します。

```
python scripts/gpu_arbiter.py status                                  # 保持者確認
python scripts/gpu_arbiter.py reap                                    # 期限切れリース回収
python scripts/gpu_arbiter.py acquire --owner comfyui --priority 10 --ttl 3600
python scripts/gpu_arbiter.py release --owner comfyui
```

`scripts/` はリポジトリ直下（`D:/Clawdbot_Docker_20260125/scripts/`）のものです。
本アプリのCLIはリースを自動取得しないので、手動で取ってから実行してください。
