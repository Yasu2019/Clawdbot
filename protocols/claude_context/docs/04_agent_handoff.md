# 04 Agent Handoff Prompt

以下を Codex CLI / Claude Code / Antigravity に渡す。

---

あなたは OpenClaw 統合エージェントです。
目的は Claude Context / Milvus / Ollama を OpenClaw に安全統合することです。

必須方針:
1. 既存 docker-compose.yml を直接破壊しない。
2. まず compose/docker-compose.claude-context.yml を overlay として起動する。
3. 既存ポートと衝突しないか確認する。
4. 既存Qdrant文書RAGとは混ぜない。
5. コード検索専用Milvusとして構成する。
6. 外部APIキーが無い場合はOllama埋め込みだけで進める。
7. 変更が必要な場合は diff を提示し、採用・部分採用・保留を判断する。
8. Portalカード追加は後段。先にMCP検索が動くことを確認する。

検証項目:
- docker psでMilvusが起動していること
- 127.0.0.1:19530が応答すること
- Ollama embedding modelが利用可能なこと
- Claude Code / Cursorから search_code が成功すること
- OpenClaw Gateway / Portal / ingest_watchdog / workflow_healer の検索が成功すること

禁止:
- 既存Qdrant collectionを削除しない
- 既存OpenClaw Gateway設定を上書きしない
- APIキーやBearer Tokenをログに出さない
- 外部API使用に勝手に切り替えない
