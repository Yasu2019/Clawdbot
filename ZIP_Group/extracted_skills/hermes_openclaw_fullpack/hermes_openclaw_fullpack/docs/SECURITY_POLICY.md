# セキュリティポリシー

## 禁止

- 会社情報・図面・顧客名・Gmail本文を外部LLMへ送信
- 本番DB、既存OpenClaw volume、業務フォルダを直接マウント
- curl | sh の無レビュー実行
- docker system prune / volume rm の自動実行
- Git reset --hard / clean -fdx の自動実行

## 必須

- 専用workspaceで検証
- コマンド実行前に guard/check-command を呼ぶ
- 操作ログを残す
- 重要ファイルはGitバックアップ後に変更
- Codex / Claude Code の二重レビューを推奨
