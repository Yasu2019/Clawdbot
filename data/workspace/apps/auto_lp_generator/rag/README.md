# RAG接続メモ

OpenClaw Gateway側のRAG API仕様に合わせて app/rag_client.py を調整してください。

想定:
- Qdrant collection: universal_knowledge / iatf_knowledge
- Gateway: http://127.0.0.1:18789
- Token: .env の OPENCLAW_BEARER_TOKEN

初期状態では、RAG未接続でもLP生成は可能です。
