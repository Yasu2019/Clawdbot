# 監査チェックリスト

| No | 確認項目 | 判定 | 証跡 |
|---|---|---|---|
| 1 | WSL2のWindowsドライブ自動マウントが無効 | □OK □NG | wsl.conf / check_wsl_isolation |
| 2 | WSL Interopが無効 | □OK □NG | powershell.exe不可視 |
| 3 | AIエージェント専用ユーザーで運用 | □OK □NG | id claw |
| 4 | Dockerコンテナが非rootまたは権限制限 | □OK □NG | compose yaml |
| 5 | docker.sockをrunnerへ渡していない | □OK □NG | compose yaml |
| 6 | 機密データの外部送信ルールがある | □OK □NG | PROMISES.secure.md |
| 7 | 例外申請フォーマットがある | □OK □NG | exception_request.md |
| 8 | 証跡取得スクリプトがある | □OK □NG | collect_evidence.sh |
