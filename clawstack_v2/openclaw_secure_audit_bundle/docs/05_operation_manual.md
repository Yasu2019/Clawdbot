# 05. 運用手順書

## 日常運用
- AIエージェント作業はWSL2内の専用workspaceで行う。
- Windows側の顧客データは直接見せない。
- 必要ファイルだけを検証用フォルダへコピーする。
- 外部APIへ送る前に、機密・個人情報・顧客名・図番を確認する。

## 週次確認
```bash
bash scripts/audit/check_wsl_isolation.sh
bash scripts/audit/collect_evidence.sh
```

## 変更時確認
- compose変更前後の差分を保存。
- ポート追加時は127.0.0.1 bindを原則にする。
- 新規MCP追加時は送信データと権限を記録する。

## ロールバック
- `/etc/wsl.conf` 変更後に不具合がある場合は旧ファイルへ戻し、Windows側で `wsl --shutdown` を実行する。
- Docker compose変更はGit差分から戻す。
