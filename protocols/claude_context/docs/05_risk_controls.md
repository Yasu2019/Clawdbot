# 05 Risk Controls

## リスク1: 外部APIへコード送信
対策: 初期設定はOllama embeddingsのみ。OpenAI/VoyageAIは明示許可まで使用禁止。

## リスク2: 既存RAGとの混線
対策: Milvusをコード専用に分離。Qdrantは文書専用のまま維持。

## リスク3: ポート衝突
使用ポート:
- 19530 Milvus gRPC
- 19091 Milvus metrics/API
- 19000 MinIO API
- 19001 MinIO Console

既存OpenClawで使っていそうな 6333, 7997, 8088, 8000, 4000, 3001 とは分ける。

## リスク4: インデックス肥大化
対策:
- node_modules, .git, dist, build, .next, __pycache__, .venv, data volumeは除外。
- generated filesを除外。

## リスク5: 古いindex参照
対策:
- git commit hash単位でindex状態を記録。
- 大きな変更後は再index。
