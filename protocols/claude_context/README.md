# OpenClaw × Claude Context 完全統合プロトコル（本気版）

目的: Zilliz Claude Context / Milvus / Ollama embeddings を OpenClaw に安全に統合し、Claude Code / Cursor / Codex CLI / Antigravity から同一のコード検索基盤を使えるようにする。

基本方針:
- 既存の OpenClaw RAG（Qdrant + Infinity + Paperless）とは分離する。
- コード検索専用に Milvus を追加する。
- 機密コードを外部へ出さないため、初期構成は Ollama 埋め込み + ローカル Milvus を標準とする。
- 導入判断は「10万行以上」「複数エージェント共有」「探索ループ削減効果あり」の3条件で行う。

対象環境:
- Windows 11 + Docker Desktop WSL2
- OpenClaw / Clawstack 既存ディレクトリ: D:\Clawdbot_Docker_20260125\clawstack_v2
- Ollama Docker service: 127.0.0.1:11434 想定
- Portal: 127.0.0.1:8088 想定
