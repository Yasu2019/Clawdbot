# 変更履歴

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
