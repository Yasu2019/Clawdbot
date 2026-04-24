# Paperclip 本気版 導入ZIP（Clawstack / OpenClaw 併用前提）

## 目的
このZIPは、既存の Clawstack / OpenClaw / LiteLLM / Langfuse / n8n / Qdrant 構成を壊さずに、
Paperclip を **AIエージェント統制レイヤ** として上乗せ導入するための実装プロトコルです。

## このZIPの前提
- 既存の主系統は維持する
- Paperclip を「司令塔の上に載せる」のではなく「エージェント統制面の補助制御」に使う
- ループバックバインド（127.0.0.1）を基本とする
- 既存ポート衝突の可能性を避けるため、Paperclip の公開側ポートは `3110` を採用する
- DB は初期導入では Paperclip 内蔵構成を優先し、本番で外部 Postgres へ移行可能にする

## 推奨導入方針
1. まず単独起動で Paperclip を確認
2. 次に OpenClaw / Codex / Claude Code を BYOA で登録
3. その後で budget / heartbeat / governance を有効化
4. 最後に n8n と通知系を足す

## 重要
このZIPは **導入プロトコル + ひな形 + 衝突回避案** です。
あなたの実機環境で実際にコマンドを実行した検証結果そのものではありません。
導入前に `09_VALIDATION_CHECKLIST.md` を必ず実施してください。
