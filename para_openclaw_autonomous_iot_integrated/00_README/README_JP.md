# PARA × OpenClaw 完全自律＋現場IoT統合パッケージ

目的：Obsidian/PARA構造を、OpenClaw・Claude Code・Codex・Paperless・Qdrant・Node-RED・ESP32ログ運用に接続し、ファイル整理、RAG登録、過去トラ学習、異常検知、改善提案を半自律〜完全自律で回すための現場投入テンプレートです。

安全方針：
- 既存フォルダは直接移動しない。まず dry-run とコピーで検証。
- 大きな変更前に Git / ZIP / ファイルバックアップを作成。
- OpenClaw/Codex/Claude には「勝手な破壊的変更禁止」を明示。
- 本番投入前に 09_Operations/checklists を確認。

推奨配置：
- Windows: C:\clawstack\para_openclaw
- WSL/Linux: ~/clawstack/para_openclaw

主な構成：
- 02_PARA_Vault: PARA保管庫テンプレート
- 03_OpenClaw: エージェント用プロンプト・スキル・安全ポリシー
- 04_Autonomous_Agent: 自動分類・異常検知・改善提案スクリプト
- 05_IoT_NodeRED: Node-RED連携フロー雛形
- 06_Qdrant_RAG: RAG登録テンプレート
- 07_Paperless: Paperless連携ルール
- 10_Local_Rebuild: セッション切れ対策のZIP再生成スクリプト
