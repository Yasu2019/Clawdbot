# Claude Code × Unity MCP 統合ガイド

## 目的
AIにシーンを直接丸投げせず、`Anime World Studio` の安全なEditor APIを介して、地形生成・草配置・性能監査を段階実行します。

## 推奨手順
1. UnityプロジェクトをGit管理し、作業ブランチを作成。
2. Unity MCPサーバー／対応パッケージを、採用する実装の公式手順に従って導入。
3. Claude Code側にMCPサーバーを登録。
4. 最初は読み取り、選択、ログ取得のみを確認。
5. 生成操作は必ず1機能ずつ実行し、Consoleエラーと性能監査を確認。
6. 問題があればGitで即時復元。

## AIに守らせる制約
- 1回の変更は1目的。
- 既存アセットを削除・上書きしない。
- 生成物は `Generated_*` 配下へ置く。
- 150万trianglesを目安に警告し、250万を超える構成は禁止。
- 全オブジェクトへのMeshCollider一括設定は禁止。
- Terrain、草、水、橋、霧、飛空艇を別タスクで作る。
- Prefab、Material、ScriptableObjectを再利用する。

## 注意
MCP実装ごとに設定ファイル名・コマンドが異なるため、このZIPには特定ベンダー固有の接続設定を固定していません。`mcp_config.example.json` を使用環境に合わせて編集してください。
