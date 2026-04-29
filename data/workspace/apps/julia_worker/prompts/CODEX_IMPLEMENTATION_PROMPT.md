# Codex Implementation Prompt

あなたは、既存の Clawstack / OpenClaw / Portal / Docker Compose 構成に、Julia Numerical Worker を安全に追加する実装担当です。

## 最重要ルール

- 既存ファイルを勝手に大規模リファクタしない。
- 既存docker-compose.ymlを直接編集しない。
- 変更前にGitバックアップを作成する。
- override compose方式で追加する。
- 既存Portalカードを削除・改名しない。
- 既存Node-REDフローを上書きしない。
- APIキーや.envをログ出力しない。
- docker compose down -v、docker system pruneは禁止。

## 作業順

1. 現在のClawstack構成を確認する。
2. Git状態を確認し、バックアップブランチまたはタグを作る。
3. ZIP内の `docker-compose.julia-worker.standalone.yml` で単独起動テストする。
4. `docker-compose.julia-worker.override.example.yml` を環境に合わせてコピー・修正する。
5. 既存compose + overrideで起動する。
6. `curl http://localhost:8096/health` と `curl http://localhost:8097/health` を確認する。
7. Portalカードを追加する。
8. OpenClaw HTTP Tool登録を提案する。
9. 変更点をレポートする。

## 成功条件

- 既存サービスが停止していない。
- Julia Workerが8096で応答する。
- Python Bridgeが8097で応答する。
- レベラー推定APIが動く。
- Portalカードが表示される。
