# 禁止コマンド・禁止操作

## Windows / PowerShell

以下は禁止。

```powershell
Remove-Item -Recurse -Force
del /s /q
rmdir /s /q
format
cipher /w
```

## Linux / WSL

以下は禁止。

```bash
rm -rf /
rm -rf ./*
sudo rm -rf
mkfs
dd if=
```

## Docker

以下は禁止。

```bash
docker compose down -v
docker volume rm
docker system prune -a --volumes
docker container prune -f
docker image prune -a -f
```

## SQL

以下は禁止。

```sql
DROP
DELETE
UPDATE
INSERT
TRUNCATE
ALTER
CREATE
GRANT
REVOKE
```

## SNS

以下は禁止。

- 無承認投稿
- 無承認ストーリー投稿
- 無承認リール投稿
- コメント自動返信
- DM自動送信
- いいね/フォロー自動化
- 非公式スクレイピング
- Cookieやセッションの盗用
- 複数アカウント大量操作

## Claude/Codexへの指示

このZIP内のスクリプトを実行する前に、必ず内容を読んでください。  
禁止操作が含まれていないことを確認してから、読み取り専用の範囲で実行してください。

