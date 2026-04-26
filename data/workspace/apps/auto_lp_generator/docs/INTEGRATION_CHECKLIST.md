# 統合前チェックリスト

## 1. ポート衝突
```bat
netstat -ano | findstr :8010
```
使用中なら .env の AUTO_LP_PORT を変更。

## 2. 既存Composeへ直接追記しない
まず単独起動。
```bat
docker compose up -d --build
```

## 3. Portal重複確認
- /apps/auto_lp_generator/ が既に存在しないか
- 既存カード名と重複しないか
- Nginx配信ルートと一致しているか

## 4. 認証
127.0.0.1 bind 前提。外部公開しない。

## 5. RAG接続
GatewayのRAGエンドポイントが異なる場合は app/rag_client.py の候補URLを追加。

## 6. AI連携
最初は AI_MODE=local_template。確認後 AI_MODE=litellm。
