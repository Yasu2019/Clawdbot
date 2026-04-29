# 05 Codex / Claude / Antigravity への実装依頼書

## 依頼目的

既存Clawstack環境へ、Google Vids向け教育動画生成ワークフローを安全に後付け統合してください。

## 前提

- 既存のDocker Compose、Portalカード、OpenClaw Gateway、Qdrant、Langfuse、Paperlessを壊さないこと。
- 既存ファイルを直接上書きしないこと。
- 大きな変更前にはGitHubまたはローカルGitでバックアップブランチを作ること。
- API消費を最小化し、ローカルLLM優先にすること。

## 実装してほしいこと

1. Portalカード追加
   - 既存Portalに `Google Vids 教育動画` カードを追加
   - 既存カードとのCSS/JS衝突を避ける

2. OpenClaw workflow追加
   - `education_video_pipeline.yaml` を読み込めるようにする
   - 入力: 文書ID、対象者、動画長、機密区分
   - 出力: script.md / storyboard.md / google_vids_prompt.md / review_sheet.md

3. RAG連携
   - Paperless/Qdrantから根拠資料を取得
   - 根拠が弱い場合は「要確認」と明記

4. セキュリティ
   - 顧客名・品番・図面番号・ロット番号・個人名をマスク
   - Google Vidsへ渡す前にマスク済みチェックを実行

5. Langfuse記録
   - 入力文書ID
   - 使用プロンプトhash
   - 生成日時
   - 承認状態
   - 生成物パス

6. 将来拡張
   - YouTube直接投稿は初期実装では行わない
   - まずはGoogle Vids貼り付け用プロンプト生成まで

## 禁止事項

- 既存Docker Compose全体の書き換え
- Portalトップページの破壊的変更
- APIキーの平文コミット
- 社外秘ファイルの外部API送信
- 承認なしのYouTube公開

## 受け入れ条件

- サンプルYAMLからGoogle Vids用プロンプトが生成できる
- Portalから手順が確認できる
- マスキングが最低限機能する
- 生成物にreview_sheet.mdが必ず含まれる
- 既存サービスが停止しない
