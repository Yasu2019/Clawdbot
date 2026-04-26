# 01 Architecture

## 推奨構成

Claude Code / Cursor / Codex CLI / Antigravity
  -> MCP client settings
  -> claude-context MCP server
  -> Milvus standalone container
  -> Ollama embedding model: nomic-embed-text or mxbai-embed-large
  -> indexed repository: D:\Clawdbot_Docker_20260125

## 既存OpenClawとの関係

既存:
- Qdrant: 文書RAG / IATF / Paperless / Docling
- Infinity: 文書向け埋め込み
- Langfuse: トレース
- Portal: 操作UI

追加:
- Milvus: コード検索専用
- claude-context MCP: コードベース検索用MCP
- watchdog: git差分・ファイル変更検知に基づく再index

## なぜQdrantへ混ぜないか

コード検索は、関数名・ファイルパス・AST単位・BM25・ベクトル検索・RRF統合が重要。
既存の文書RAGに混在させると、品質文書、PDF、IATF文書、コード断片が同じ検索空間に混ざり、検索ノイズが増える。
そのため、最初はMilvusをコード専用DBとして分ける。
