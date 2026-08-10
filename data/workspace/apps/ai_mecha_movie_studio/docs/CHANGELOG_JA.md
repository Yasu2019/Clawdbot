# 変更履歴

## V3.2 (2026-08-11)

ComfyUI連携を「READMEだけ」から「実ワークフローを登録して実際に通せる」状態にしました。

### 追加

- `workflows/scail2/scail2_wan_api.json` — 稼働中ComfyUI 0.24.0 の `WanSCAILToVideo`
  実シグネチャに合わせたAPI形式ワークフロー（19トークン）。構造は実機の `/object_info` で検証済み。
- `workflows/smoke/comfyui_sd15_txt2img_api.json` — GPU不要の疎通確認用SD1.5ワークフロー。
- `scripts/run_comfy_workflow.py` — 置換 → 事前検証 → 投入 → 完了待ち → 出力回収 を行うCLI。
  `--preset` で既定値、`--set KEY=VALUE` で上書き、`--check-only` で投入せず検証のみ。

### `adapters/comfyui.py` の変更

- **数値トークンの型を保持**: 文字列全体がちょうど `{{TOKEN}}` の場合、値をそのままの型で埋める。
  従来は全て文字列化されるため、INT/FLOAT入力（width/steps/cfg等）が型エラーになった。
- **未置換トークンの検出**: 置換後に `{{...}}` が残っていれば投入前に落とす。
- **`validate_workflow()`**: 投入前に `/object_info` と突合し、存在しないノード・入力名・
  候補外の値（＝モデル未配置）を列挙する。
- **エラー本文の可視化**: ComfyUIはバリデーション失敗を400のJSON本文で返すが、従来は
  `HTTPError` が素通りして内容が読めなかった。`ComfyError` に要約と生JSONを保持する。
- **`wait_for_result()` / `collect_outputs()` / `download_output()` / `run_workflow()`**:
  従来は投入するだけで結果を取得する手段が無かった。`/history` ポーリングで完了を待ち、
  出力ファイルを `/view` から回収できるようにした。

### 実測（2026-08-11 / ComfyUI 0.24.0 Docker・CPU実行）

- SD1.5疎通: 256x256/6steps=29秒、384x384/20steps=65秒。いずれもPNGを取得して目視確認済み。
- SCAIL-2: 19トークンの置換とグラフ構造は有効。不足は重み4件
  （diffusion_models / text_encoders / vae / clip_vision）のみで、事前検証がそれを特定する。

### 既知の制約

- 接続先ComfyUIは `--cpu` 起動（`torch 2.12.0+cpu`）でGPUを使っていない。Wan 14B級の
  実用生成にはGPU有効化が必要。
- `POSE_VIDEO_PATH` は**ComfyUIプロセスから見たパス**を渡す必要がある（Docker運用のため
  Windows側のパスは通らない）。

## V3.1 (2026-08-10)

V3を実機（Windows 11 / Python 3.10.11 / RTX 5060 Ti 16GB / Ollama qwen3:8b）で動作検証し、
判明した不具合を修正しました。設計方針（BAT/PS1なし・shell=True不使用・自動pip/DLなし・
AI応答をコマンド実行しない）は変更していません。

### 修正

1. **PATH外のツールを検出できず、計画と実行が矛盾する問題**
   `blender` はインストール済みでも既定でPATHに入らないため `shutil.which()` では検出できず、
   AIの計画に「Blender再利用」と出るのに実行時は「見つかりません」で失敗していました。
   `core/scanner.py` に `resolve_tool()` を追加し、PATH → 既知インストール先
   （`C:/Program Files/Blender Foundation/*`、WinGetのFFmpeg、Ollama等）の順で解決します。
   検出結果には `tools_off_path` として「PATH外で見つけたツール」を明示します。
   `adapters/blender.py` `ffmpeg.py` `remotion.py` も `resolve_tool()` を使うよう変更しました。

2. **AIの再利用候補を検出結果と突合していなかった問題**
   ComfyUI未インストールの環境でも、AIが `reuse` に ComfyUI / WhisperX / MediaPipe を
   列挙することがありました。`core/planner.py` で `availability()` により検出フラグを作り、
   `reuse` は検出済みと確認できたものだけを残し、残りは `reuse_unverified` へ分離します。
   突合結果は `detected` キーに出力し、未検証項目があれば `risks` へ警告を追加します。
   （ルールベースのフォールバック経路にも同じ検証を適用します）

3. **TkinterをワーカースレッドからUI更新していた問題**
   `gui.py` の検出／AI判定／疎通テストが別スレッドから直接ウィジェットを更新しており、
   長時間実行やボタン連打で固まる可能性がありました。`queue.Queue` + `after()` による
   メインスレッド反映へ変更し、各ワーカーに例外ハンドラを追加しました。
   ComfyUI確認も応答待ちでUIが止まらないよう別スレッド化しました。

   さらに検証中、**「1. システム検出」がワーカースレッド内で `self.roots.get()` を呼んでおり、
   Tkの `main thread is not in main loop` で失敗する**ことを確認しました
   （V3では例外ハンドラが無いため、スレッドが黙って死んで結果が出ないだけでした）。
   入力ウィジェットの読み取りをスレッド起動前のメインスレッド側へ移動しました。
   AI判定の Ollama URL / モデル名も同様に修正しています。

4. **探索ルートが C:/ D: 決め打ちだった問題**
   `core/scanner.py` を固定ドライブ列挙（Windowsは DRIVE_FIXED のみ。ネットワークドライブは
   走査しない）に変更し、各ドライブの `AI` / `Tools` / 直下のComfyUI等を候補にします。
   環境変数 `MECHA_STUDIO_EXTRA_ROOTS`（`;`区切り）でも探索ルートを追加できます。

5. **稼働中サービスを検出できなかった問題**
   検証環境ではComfyUIの**フォルダは存在しないのにAPI（127.0.0.1:8188）は応答**していました
   （Docker等で稼働中）。フォルダ検出だけでは「ComfyUIなし」と誤判定するため、
   `core/scanner.py` に読み取り専用の疎通確認を追加し、結果を `services` キー
   （`comfyui_api` / `ollama_api`）として出力します。`planner.availability()` は
   フォルダとAPIのどちらかがあれば再利用可能とみなします。

### その他

- 配布ZIPから `__pycache__` を除外しました（V3には Python 3.13 の `.pyc` が混入していました）。
- `adapters/remotion.py` の未使用 import を削除しました。

### 未対応（既知）

- `workflows/scail2` `workflows/wan22` `workflows/audio` はREADMEのみで、実ワークフローJSONは
  未同梱です。ComfyUIで「API Format」保存したJSONを各フォルダへ登録してください。
