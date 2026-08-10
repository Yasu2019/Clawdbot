# 疎通確認用ワークフロー

`comfyui_sd15_txt2img_api.json` — SD1.5 txt2img。ComfyUI連携そのものが動くかを
最小構成で確認するためのものです。重いモデルを必要としないので、GPUが無くても通ります。

## 実行

```
python scripts/run_comfy_workflow.py workflows/smoke/comfyui_sd15_txt2img_api.json \
    --preset sd15 --wait --dest workspace/sample_mecha_movie/output/comfyui
```

トークンは `--set KEY=VALUE` で上書きできます。値はJSONとして解釈するため、
`--set STEPS=20` は整数、`--set CFG=7.5` は浮動小数、それ以外は文字列になります。

## 実測（2026-08-11 / ComfyUI 0.24.0 CPU実行）

| 設定 | 所要 | 出力 |
|---|---|---|
| 256x256 / 6 steps | 29秒 | `mecha_studio_smoke_00001_.png` |
| 384x384 / 20 steps | 65秒 | `mecha_studio_sample_00001_.png` |

CPU実行のため、これ以上の解像度・ステップ数は現実的ではありません。
