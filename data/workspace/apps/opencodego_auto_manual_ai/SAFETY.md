# 安全設計

このZIPは既存環境を壊さないため、標準では以下の制約を持ちます。

- 入力動画は読み取り専用
- 出力は outputs/ のみ
- DB接続なし
- 既存Docker volume操作なし
- PortalカードはサンプルJSONのみ。自動上書きしない
- docker-compose.addon.example.yml は例。既存composeに直接追記しない

Codex/Claudeへの指示:
危険なコマンド、DB write、volume削除、環境ファイル上書きが必要になった場合は即停止し、人間承認を求める。
