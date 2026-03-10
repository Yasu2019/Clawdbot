# Clawstack 可観測性アーキテクチャ v1.0

> 作成: 2026-03-09 | 対象: clawstack-unified

---

## 1. 目的

LLM呼び出し・RAG・MCP・n8n・外部API のすべてのトレースを Langfuse に集約し、
品質スコア・コスト・レイテンシを一元監視する。

---

## 2. 現状の結線確認

```
[OpenClaw/Claude]
    │
    ├── MCP: clawstack-tools (port 9876)
    │       ├── rag_search  → Infinity(embed) → Qdrant
    │       └── web_search  → SearXNG
    │
    ├── MCP: n8n-workflows (port 5678)
    │       └── execute_workflow → n8n → (downstream)
    │
    └── LLM: LiteLLM Proxy (port 4000)
             ├── google/gemini-2.5-flash  ← primary
             ├── ollama/qwen2.5-coder:7b  ← fallback
             └── [callback] → Langfuse ✅ (already wired)
```

### 確認済みの結線

| 接続 | 状態 | 備考 |
|------|------|------|
| LiteLLM → Langfuse | ✅ 有効 | `success_callback: ["langfuse"]` 設定済み |
| Langfuse サービス | ✅ 起動中 | `http://langfuse:3000` (host: 3001) |
| Langfuse SDK in gateway | ✅ インストール済み | `from langfuse import Langfuse` 確認済み |
| clawstack-tools MCP | ✅ コード完成 | gateway 再起動後に有効化 |

---

## 3. トレース設計

### 3.1 親 trace = 1リクエスト

```
Trace: request_id (UUID)
├── Span: mcp.rag_search
│   ├── Input: query, collection, top_k
│   ├── Output: result_count, top_score
│   └── Metadata: embed_ms, search_ms, model
│
├── Span: mcp.web_search
│   ├── Input: query, engines
│   └── Output: result_count
│
├── Span: n8n.execute_workflow
│   ├── Input: workflow_id, payload
│   └── Output: status, output_size
│
└── Generation: litellm.chat (自動計測済み via LiteLLM callback)
    ├── Model: google/gemini-2.5-flash
    ├── Usage: prompt_tokens, completion_tokens
    └── Cost: USD
```

### 3.2 request_id 伝播

- MCP tool 呼び出し時に `X-Request-ID` ヘッダーを付与（将来的拡張）
- 現在: `session_id` をランダム生成し Langfuse metadata に付与

### 3.3 スコアリング

| スコア名 | 値域 | 計算方法 |
|---------|------|---------|
| rag_relevance | 0.0–1.0 | Qdrant top-1 コサイン類似度 |
| response_latency | ms | MCP tool 実行時間 |
| tool_success_rate | 0.0–1.0 | 成功/全試行 (セッション累計) |

---

## 4. 実装計画

### Phase 2: clawstack_tracing.py (ユーティリティ)

```python
# ライブラリ提供:
# - ClawTrace: Langfuse Trace ラッパー
# - span_rag_search(trace, query, result): MCP span 記録
# - span_web_search(trace, query, result): MCP span 記録
# - span_n8n(trace, workflow_id, result): n8n span 記録
```

### Phase 2: clawstack_mcp_server.py 更新

- 各ツール呼び出し時に Langfuse span を記録
- `try/except` で tracing failure を無音で握り潰す（観測系は本体に影響させない）

### Phase 3: Portal 可観測性Hub

- `http://localhost:8088/apps/observability_hub/` でアクセス
- Langfuse API を直接呼び出してメトリクス表示
- 自動リフレッシュ (30秒)

### Phase 4: ベンチマーク

- `data/workspace/docs/rag_benchmark.json` に期待値セット定義
- Langfuse Score API でベンチ結果を記録

---

## 5. Langfuse API キー

```
LANGFUSE_PUBLIC_KEY=pk-lf-clawstack-2026
LANGFUSE_SECRET_KEY=sk-lf-clawstack-2026
LANGFUSE_HOST=http://langfuse:3000
```

> ⚠️ 初回利用前に `http://localhost:3001` でユーザー登録が必要

---

## 6. 今後の拡張

- **LangSmith 比較モード**: `.env` に `LANGSMITH_API_KEY` を追加、LiteLLM に `langsmith` callback を追加
- **Telegram アラート**: 品質スコア < 0.4 または レイテンシ > 10秒 で n8n 経由通知
- **CETOL6 再インジェスト**: OCR品質改善後のスコア比較
