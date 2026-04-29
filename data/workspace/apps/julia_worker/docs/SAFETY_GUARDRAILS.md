# Safety Guardrails

## 絶対ルール

1. 既存Clawstackの本体ファイルを勝手に大規模変更しない。
2. 既存 `docker-compose.yml` を直接編集しない。
3. 必ずGitバックアップを取得してから変更する。
4. まず単独起動で確認する。
5. 既存Portalカードを削除・改名しない。
6. 既存Node-REDフローを上書きしない。
7. 認証情報、APIキー、Wi-Fiパスワードをコミットしない。
8. Julia Workerにファイル書き込み権限を持たせない。
9. いきなり本番データで実行しない。
10. 計算結果は簡易推定として扱い、正式判断は実測・CAE・品質基準で確認する。

## AIツールへの禁止指示

Codex / Claude / Gemini / OpenCode GO / Antigravity / VSCode Agent に共通で伝えること:

- 勝手なリファクタリング禁止
- 既存UIのデザイン変更禁止
- 既存ポート変更禁止
- 既存DB変更禁止
- 既存ボリューム削除禁止
- docker compose down -v 禁止
- prune系コマンド禁止
- APIキー表示禁止
- `.env` の中身をログ出力しない
