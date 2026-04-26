# 安全設計

## DB
- READ ONLYユーザーのみ使用。
- SQL GuardでSELECT/WITH以外を拒否。
- 禁止語句: UPDATE, DELETE, INSERT, MERGE, DROP, ALTER, TRUNCATE, EXEC, CREATE。

## HITL
- 外部送信、報告書リリース、DBクエリ実行前に承認を要求。

## 外部API
- 初期値は `ALLOW_EXTERNAL_SEND=false`。
- 画像生成はプロンプト生成までを基本とし、機密図面や顧客ロゴの送信は禁止。
