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

## ポート方針（2026-08-06 改訂：排他ルールを廃止）

当初は GPU版 と Docker CPU版 が同じ 8188 を奪い合っていたため「排他運用」にしていたが、
人間が覚えるルールは事故るので**物理的に衝突しない構成へ変更**した。

| 実体 | ホスト側ポート | 位置づけ |
|---|---|---|
| **ネイティブGPU版**（本キットが起動） | **8188** | **正**。既存コードの `COMFYUI_URL` 既定値がここを指す |
| Docker CPU版 (`services/comfyui`) | **18188** | 非常用フォールバック。GPUが落ちた時だけ使う |

`start_comfyui_gpu.py` の8188占有チェックは安全弁として残してある（GPU版の二重起動防止）。

## GPU調停（RL学習・FEM との共存）

RTX 5060 Ti は GeForce系のため **MIG非対応**で、16GBのVRAMを論理分割できない。
同時実行は必ずどちらかがOOMする（`trouble_history`: RL学習resume中の `RuntimeError: bad allocation`）。
そこで **`scripts/gpu_arbiter.py` によるリース方式の時分割**で調停する。

```
python scripts/gpu_arbiter.py status                # 現在の保持者とVRAM
python scripts/gpu_arbiter.py acquire --owner rl_train --priority 0 --ttl 21600 --nonpreemptible
python scripts/gpu_arbiter.py release --owner rl_train
python scripts/gpu_arbiter.py reap                  # 死んだ保持者のリース回収
```

| 用途 | priority | 横取り |
|---|---|---|
| RL学習 / CAEソルバ（長時間・中断＝損失） | 0 | 不可（`--nonpreemptible`） |
| ComfyUI 生成 | 10 | 可 |
| バッチレンダ | 20 | 可 |

**ComfyUIの譲り方（実測に基づく二段構え）**

1. `POST /free {"unload_models":true,"free_memory":true}` を送る
2. VRAMが戻るまで最大180秒待つ
3. 戻らなければ**プロセスを終了**して確実に解放する

**実測（2026-08-06 K10）**

| 条件 | 結果 |
|---|---|
| `--reserve-vram 1.5` 起動 → 生成直後に `/free` | **t+6秒で解放**（空き 9231 → 15855 MiB） |
| `--reserve-vram` なし起動 → アイドル時に `/free` | 60秒以内に戻らず。その後（数分内）に解放を確認 |
| プロセス終了 (`taskkill /F`) | **即時に全解放**（空き 16050 MiB） |

つまり `/free` は通常数秒で効くが、**常に速いとは限らない**。`comfy_aimdo` が
`vrambuf_create` で確保したVRAMバッファの解放タイミングに依存するため、
待ち時間だけに賭けず**プロセス終了のフォールバックを必ず持つ**設計にしてある。

**予防策**: `--reserve-vram <GB>` で他ジョブ用の空きを常時確保できる（`comfy_aimdo` の
`simple_vram_headroom` に渡る）。`config/settings.json` の `reserve_vram_gb` が既定値。

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
