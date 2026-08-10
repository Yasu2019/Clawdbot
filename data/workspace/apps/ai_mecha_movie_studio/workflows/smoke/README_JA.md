# 疎通確認用ワークフロー

`comfyui_sd15_txt2img_api.json` — txt2img の最小構成。ComfyUI連携そのものが動くかを
確認するためのものです。チェックポイント名はトークンなので、SD1.5でもSDXLでも使えます。

## 実行

```
python scripts/run_comfy_workflow.py workflows/smoke/comfyui_sd15_txt2img_api.json \
    --preset sdxl --wait --dest workspace/sample_mecha_movie/output/comfyui_gpu
```

プリセット:

| プリセット | チェックポイント | 用途 |
|---|---|---|
| `sdxl` | `sd_xl_base_1.0.safetensors` | 本番GPU機（8188）の在庫 |
| `sd15` | `v1-5-pruned-emaonly.safetensors` | Docker CPU版（18188）の在庫 |

トークンは `--set KEY=VALUE` で上書きできます。値はJSONとして解釈するため、
`--set STEPS=20` は整数、`--set CFG=7.5` は浮動小数、それ以外は文字列になります。

## 実測（2026-08-11）

| 実行環境 | 設定 | 所要 |
|---|---|---|
| Docker CPU版 (18188) | SD1.5 256x256 / 6 steps | 29秒 |
| Docker CPU版 (18188) | SD1.5 384x384 / 20 steps | 65秒 |
| **ネイティブGPU版 (8188)** | SDXL 1024x1024 / 20 steps（初回・モデルロード込み） | **131秒** |
| **ネイティブGPU版 (8188)** | SDXL 1024x1024 / 20 steps（ウォーム） | **11秒** |

いずれもPNGを取得して目視確認済み。GPU側はVRAM 6.8GB / 16.3GB 使用。
