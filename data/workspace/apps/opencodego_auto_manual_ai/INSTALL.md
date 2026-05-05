# 導入手順

## 1. まずZIPを展開
推奨配置:
D:\Clawdbot_Docker_20260125\addons\auto_manual_ai

## 2. 既存環境確認
protocols/00_existing_system_check.md をCodex/Claudeに読ませ、競合確認を行う。

## 3. Python仮想環境
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. ffmpeg確認
```powershell
ffmpeg -version
```
未導入の場合は、既存Clawstackの動画処理コンテナやWindows ffmpegを利用する。

## 5. 動画処理テスト
```powershell
python scripts\auto_manual_pipeline.py input.mp4 --out outputs\test --chunk-minutes 5 --frame-interval 2
```

## 6. OpenCodeGO実行
prompts/opencodego_main_prompt.md と outputs/test/ai_packets/*.json を使い、チャンクごとの手順書を生成する。

## 7. 統合
prompts/final_merge_prompt.md で final_manual.md に統合する。

## 8. HTML化
```powershell
python scripts\render_manual_html.py outputs\final_manual.md --out outputs\final_manual.html
```
