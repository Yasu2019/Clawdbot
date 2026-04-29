# Failure Patterns

## やってはいけない失敗

1. Pythonアプリ全体をJuliaに置き換えようとする
2. 既存Portalを全面リニューアルする
3. 既存docker-compose.ymlを直接編集して壊す
4. Node-RED既存フローを上書きする
5. Juliaの初回起動遅延を故障と誤認する
6. 簡易モデル結果を正式CAE結果として扱う
7. ポート衝突を確認しない
8. Windows/WSLのパス差異を無視する
9. docker compose down -vでボリュームを消す
10. APIキーをログに出す

## 正しい対応

- 追加方式で統合する
- まず単独起動
- 次にoverride統合
- 最後にPortal/OpenClaw/Node-RED連携
