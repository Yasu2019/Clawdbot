# Codexレビュー依頼書

## 依頼
このZIPは、OpenClaw/Clawstack V2にBlender自然動作生成パイプラインを統合する候補です。既存環境を最も理解しているCodexが、融合すべきか、別プロジェクトとして知見蓄積すべきか判断してください。

## 必須確認
- 既存Portalカード形式との整合
- 既存Docker Composeとの衝突
- 既存MCP設定との衝突
- Blenderのバージョン
- Python環境
- OpenCodeGO/DeepSeek/Qwenの呼び出し方
- セキュリティ上、外部サイトから自動ダウンロードしてよいか

## 判定基準
A: すぐ統合可能
B: サンドボックスで検証後に統合
C: まだ統合せず、ノウハウとして保存

## 禁止
- 既存DB、Docker volume、Minio、Qdrant、Postgresを削除しない
- Portalの既存カードを上書きしない
- Blenderアドオンを無確認で大量導入しない
- 著作権不明モーションを社外公開用途に使わない
