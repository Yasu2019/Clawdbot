# OpenCodeGO × Auto Manual AI 本気版全部入りプロトコル

目的: 1時間前後の画面録画動画から、OpenCodeGO系AIモデルを主役にして、操作手順書・作業標準書・教育資料・監査エビデンスを自動生成するための統合プロトコルです。

重要方針:
- 既存Clawstack/OpenClaw環境を壊さない
- まず現状調査し、統合/部分採用/保留をCodex/Claude/Gemini側が判断する
- 動画を丸ごとAIに投げず、ローカル前処理で分割・重要フレーム抽出・OCR候補化する
- OpenCodeGOのDeepSeek/Qwen/Coder系モデルを主役にする
- Gemini等の外部APIは任意・保留扱い。APIコストと機密情報流出を避ける
- 品質/IATF用途に使える出力形式を優先する

想定出力:
- HTML手順書
- Markdown手順書
- Word変換用Markdown
- PDF変換用HTML
- 教育用チェックリスト
- 監査エビデンス一覧
- 操作リスク/注意点一覧

最初に読む順番:
1. protocols/00_existing_system_check.md
2. protocols/01_architecture.md
3. protocols/02_video_pipeline.md
4. prompts/opencodego_main_prompt.md
5. scripts/auto_manual_pipeline.py
