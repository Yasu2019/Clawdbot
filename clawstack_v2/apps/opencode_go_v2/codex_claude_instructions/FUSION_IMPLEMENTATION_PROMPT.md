# Codex / Claude / Antigravity向け実装指示

既存Clawstack環境へ、OpenCode GO融合拡張パックを安全に取り込んでください。

## 最重要ルール
1. 既存ファイルを勝手に上書きしない。
2. 変更前に git status を確認する。
3. バックアップブランチを作る。
4. docker-compose.ymlの全面書き換えは禁止。
5. Portalカード追加はID重複を確認する。
6. OpenCode GOへ送るデータは公開情報または匿名化済み情報のみ。
7. Gmail、図面、Paperless NGX原文、社内情報を外部AIへ送信しない。
8. 本番反映はユーザー承認後のみ。

## 実装優先順位
policies → agents → DBスキーマdev検証 → Portalカードdev追加 → LiteLLM追記 → n8n/Node-RED outline登録。
