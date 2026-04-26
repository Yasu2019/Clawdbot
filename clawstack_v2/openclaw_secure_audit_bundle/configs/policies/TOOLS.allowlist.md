# TOOLS.allowlist.md - AIエージェント許可ツール方針

## 原則許可
- `ls`, `cat`, `grep`, `find`, `sed`, `awk`
- `python` によるローカル解析
- `git diff`, `git status`
- `docker compose ps`, `docker compose logs --tail=200`

## 条件付き許可
- `npm install`, `pip install`: ロックファイル・取得元確認後
- `curl`, `wget`: 送信先確認後
- `docker compose up`: 対象composeファイル確認後

## 原則禁止
- `sudo` を伴う自律実行
- `rm -rf` の広範囲実行
- Windows側コマンド実行
- `docker run --privileged`
- `/var/run/docker.sock` のマウント
