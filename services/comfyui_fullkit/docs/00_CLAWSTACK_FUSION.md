# 00 Clawstack融合仕様（本キットを読む前に必ずここから）

作成: 2026-08-06 / 元ZIP: `ZIP_Group/ComfyUI_RTX5060Ti16GB_FullKit_20260805.zip`
関連Beads: `Clawdbot_Docker_20260125-ggli`

## 何が変わったか

元キットは「C:\AI に ComfyUI Portable を新規導入する単体キット」だった。
Clawstackには**既にGPU実行可能なComfyUI本体**があるため、本体は新規導入せず**既存資産を再利用**する形に融合した。

| 項目 | 元キット | 融合後（本ディレクトリ） |
|---|---|---|
| ComfyUI本体 | `C:/AI/ComfyUI_windows_portable/ComfyUI` を新規導入 | `vnccs_comfyui_clawstack_pro/ComfyUI_app`（既存）を再利用 |
| 実行Python | Portable同梱 | `vnccs_comfyui_clawstack_pro/.venv_hunyuan3d`（torch 2.8.0+cu128 / CUDA有効） |
| モデル保存先 | ComfyUI配下 | `F:/clawstack_data/comfyui_models`（CLAUDE.md: 100MB超はF:） |
| モデル参照 | 直置き | `ComfyUI_app/extra_model_paths.yaml` で追加参照（既存modelsは無改変） |
| 起動 | `run_nvidia_gpu.bat` | `scripts/start_comfyui_gpu.py`（8188占有チェック付き） |

## 絶対ルール：8188はひとつだけ

`services/comfyui`（**Docker CPU-only**）と本キットが起動するネイティブGPU版は**同じ 127.0.0.1:8188**を使う。
両方立てると、API側は成功しているのに**無言でCPU実行**になり、生成が数十倍遅くなる。

- `start_comfyui_gpu.py` は起動前に8188を検査し、使用中なら**起動を拒否**する
- 迷ったら `python scripts/doctor.py` の「ポート排他」節を見る
- Docker側を止める: `docker compose -f services/comfyui/docker-compose.yml down`

## 既存Clawstack連携（今回コード改変なし）

すでに8188を前提に動くものがあり、GPU版を起動すればそのまま品質が上がる。

| 連携先 | 参照方法 |
|---|---|
| `clawstack_v2/apps/iatf_video_factory/pipeline/comfyui_upscaler.py` | 環境変数 `COMFYUI_URL`（既定 `http://127.0.0.1:8188`） |
| `scratch/video_comfyui_processor.py`, `scratch/video_orchestrator.py` | 同8188 |
| `data/workspace/portal.html`, `apps/creative_studio/index.html` | 「Raw ComfyUI」リンク |

本キットの `scripts/comfy_api_client.py` も同じ `COMFYUI_URL` を優先する。

## 手順（融合後の正しい順番）

```
python scripts/doctor.py                       # 1. GPU/本体/venv/容量/ポートを診断
python scripts/setup_model_paths.py            # 2. extra_model_paths.yaml を生成（F:参照）
python scripts/model_manager.py list           # 3. 導入可能モデル一覧
python scripts/model_manager.py install sdxl_base   # 4. SDXL 6.46GB
python scripts/start_comfyui_gpu.py            # 5. GPU起動（別ターミナル）
python scripts/comfy_api_client.py             # 6. SDXL疎通テスト
```

動画（Wan2.2 TI2V 5B, 計16.9GB）に進む場合:

```
python scripts/model_manager.py install wan22_5b
python scripts/download_official_workflows.py
```

## 実測値（2026-08-06 / K10）

| モデル | サイズ |
|---|---|
| `sd_xl_base_1.0.safetensors` | 6.46 GB |
| `wan2.2_ti2v_5B_fp16.safetensors` | 9.31 GB |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.27 GB |
| `wan2.2_vae.safetensors` | 1.31 GB |

GPU: RTX 5060 Ti 16311 MiB / driver 610.62。

## 重複キットについて

`ZIP_Group/extracted/krea2_comfyui_rtx5060ti_pack` は同系統の先行キット（Krea2 + Unity連携）。
**ComfyUI運用の正はこの `services/comfyui_fullkit`** とし、krea2側はUnity連携部分の参照専用とする。

## 品質ルール（省略禁止）

- 生成画像・動画は**必ず実ファイルを目視確認**してから合格判定する（グローバルルール / 数値のみの合格判定は禁止）
- 新規・改変Pythonは先頭で `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`（P023）
- VRAM不足時は **解像度 → フレーム数 → steps** の順に下げる（`docs/02_RTX5060Ti推奨設定.md`）
