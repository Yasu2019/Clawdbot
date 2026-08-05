# ComfyUI RTX 5060 Ti 16GB 全部入り本気版

> **⚠️ Clawstack融合済み。まず [`docs/00_CLAWSTACK_FUSION.md`](docs/00_CLAWSTACK_FUSION.md) を読むこと。**
> 本体は新規導入せず既存 `vnccs_comfyui_clawstack_pro/ComfyUI_app` を使う。モデルはF:に置く。
> 8188は `services/comfyui`(Docker CPU版) と排他。以下「最短手順」の 1・5・6 は融合後は不要/変更済み。

対象: Windows 11 / NVIDIA RTX 5060 Ti 16GB / メモリ32GB以上推奨
作成日: 2026-08-05 / Clawstack融合: 2026-08-06

## 重要
このZIPには巨大なAIモデル本体（数十GB）は同梱していません。
公式配布元から必要なものだけを取得し、ComfyUIの正しいフォルダへ配置するためのツール一式です。
BAT/PowerShellは含めていません。過去のウイルス対策ソフト誤検知を避けるため、すべてPythonとテキストで構成しています。

## 最短手順
1. ZIPを `C:\AI\ComfyUI_FullKit` など半角英数字の短いパスへ展開
2. WindowsにPython 3.11以上をインストール
3. コマンドプロンプトで展開先へ移動
4. `python scripts\doctor.py` を実行
5. ComfyUI Portableを公式サイトから取得・展開
6. `config\settings.json` の `comfyui_root` を実際のComfyUIフォルダへ修正
7. `python scripts\model_manager.py list` でモデル一覧を確認
8. 最初は `python scripts\model_manager.py install sdxl_base` を実行
9. 動画は `python scripts\model_manager.py install wan22_5b` を実行
10. `python scripts\download_official_workflows.py` で公式動画ワークフローを取得
11. ComfyUIを起動し、`workflows` のJSONを読み込む

## 推奨導入順
- SDXL Base: 画像生成の動作確認
- Wan2.2 TI2V 5B: RTX 5060 Ti 16GB向けの本命動画モデル
- HunyuanVideo 1.5: 余裕ができてから。720pは処理時間とRAM使用量が大きい

## 同梱物
- `scripts/doctor.py`: GPU、Python、空き容量、ComfyUI配置診断
- `scripts/model_manager.py`: 公式モデルの選択ダウンロード、再開、SHA256記録
- `scripts/comfy_api_client.py`: ComfyUI APIへの画像生成サンプル
- `scripts/workflow_inspector.py`: ワークフロー内の必要モデル名を抽出
- `config/settings.json`: ComfyUI設置場所・保存先設定
- `config/models.json`: モデルURL・配置先マニフェスト
- `workflows/`: SDXL APIサンプルと公式動画ワークフロー取得案内
- `docs/`: 導入、VRAM設定、トラブル対応、長尺動画化

## 安全上の方針
- 管理者権限を要求しません
- レジストリを変更しません
- Windows Defenderの除外設定を自動変更しません
- スタートアップ登録やタスク登録を行いません
- ダウンロード元は公式GitHubまたは公式Hugging Faceのみ
- ダウンロード後にSHA256を計算して `logs/download_hashes.json` に保存

## 16GB VRAM初期値
### SDXL
- 1024x1024
- 20〜30 steps
- batch 1

### Wan2.2 5B
- 初回: 640x384、81 frames、16〜20 steps、24fps
- 安定後: 832x480または960x544
- 1280x704/121 framesは動作確認後
- 他のGPUアプリを閉じる

## 起動
ComfyUI Portable付属の公式 `run_nvidia_gpu.bat` を使用してください。
本ZIPは独自のBATを生成しません。
