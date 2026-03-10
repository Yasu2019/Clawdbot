# Clawstack 技術指示版 v1.0
**作成日**: 2026-03-10
**用途**: Antigravity / 実装エージェント向け — 最小差分・優先順位付き実装指示
**対象プロトコル**: CLAWSTACK_SYSTEM_PROTOCOL_v2.1.md
**原則**: 破壊的変更禁止 / --no-cache禁止 / 秘密情報外部送信禁止 / 変更前影響確認必須

---

## 優先度マップ

| 優先度 | タスク | リスク | 推定工数 |
|--------|--------|--------|---------|
| P1 🔴 | Redis auth 警告修正 | 低 | 5分 |
| P2 🟠 | request_id をトレーシングに追加 | 低 | 30分 |
| P3 🟠 | RAGクエリ日→英自動補完 | 低〜中 | 1時間 |
| P4 🟡 | Docling → ingest パイプライン強化 | 中 | 2時間 |
| P5 🟡 | ClickHouse TTL / データ保持設定 | 低 | 30分 |
| P6 🟢 | Portal Hub に KPI カード追加 | 低 | 1時間 |
| P7 🟢 | Qdrant snapshot n8n ワークフロー | 低 | 1時間 |

---

## P1: Redis auth 警告修正

### 問題
Langfuse web / worker が Redis に接続時にパスワードを送信するが、Redis はパスワード未設定。
ログに大量の `ERR AUTH <password> called without any password configured` が出る。

### 原因
Langfuse コンテナに `REDIS_AUTH` が未設定のため、ライブラリのデフォルト動作でパスワードを送る。

### 修正: `clawstack_v2/docker-compose.yml` 差分

```yaml
# langfuse サービスの environment に追加
  langfuse:
    environment:
      # --- 既存の行はそのまま ---
      - REDIS_AUTH=          # ← 追加: 空文字でパスワードなしを明示

  langfuse-worker:
    environment:
      # --- 既存の行はそのまま ---
      - REDIS_AUTH=          # ← 追加: 空文字でパスワードなしを明示
```

### 適用コマンド
```bash
cd clawstack_v2
docker compose up -d --force-recreate langfuse langfuse-worker
```

### ロールバック
```bash
# REDIS_AUTH= 行を削除して同コマンドを再実行
```

---

## P2: request_id / session_id をトレーシングに追加

### 問題
現在の `ClawTrace` は各MCP呼び出しに独立したトレースを作成しており、
1つのユーザーリクエスト全体を横断追跡できない。

### 修正: `clawstack_tracing.py` の `ClawTrace.__init__` に引数追加

```python
# 変更箇所のみ表示（既存コードに追記）

class ClawTrace:
    def __init__(
        self,
        name: str = "clawstack_session",
        metadata: dict = None,
        request_id: str = None,   # ← 追加
        session_id: str = None,   # ← 追加
        user_id: str = "openclaw",# ← 追加
    ):
        import uuid
        self.name       = name
        self.metadata   = metadata or {}
        self.request_id = request_id or str(uuid.uuid4())
        self.session_id = session_id
        self.user_id    = user_id
        self._lf        = None
        self._root      = None

    def start(self):
        self._lf = _get_client()
        if self._lf is None:
            return self
        try:
            combined_meta = {
                **self.metadata,
                "request_id": self.request_id,
            }
            if self.session_id:
                combined_meta["session_id"] = self.session_id
            self._root = self._lf.start_span(
                name=self.name,
                input=combined_meta,
            )
        except Exception as e:
            logger.warning(f"[tracing] start_span failed: {e}")
        return self
```

### MCP サーバー側: `clawstack_mcp_server.py` でヘッダーから request_id を受け取る（将来拡張）

```python
# 現状は uuid 自動生成で対応。OpenClaw 側から X-Request-ID ヘッダーを渡す拡張は将来実装。
# 現時点の最小対応: span metadata に request_id を記録するだけで追跡可能。
```

---

## P3: RAGクエリ 日本語→英語 自動補完

### 問題
`universal_knowledge` の CETOL/FEM 文書は VLM 英語説明で取り込まれているため、
日本語クエリでは類似度スコアが低い（0.4〜0.5台）。

### 修正: `clawstack_mcp_server.py` に翻訳補完を追加

```python
# _translate_to_english() を追加 (qwen2.5-coder:7b に翻訳させる)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

def _translate_query(query: str, collection: str) -> str:
    """
    CETOL/FEM コレクションは英語クエリが有効。
    日本語が含まれる場合は Ollama で英訳して補完クエリを作る。
    失敗時は元のクエリを返す（本体に影響させない）。
    """
    # CETOL/FEM 向けのみ翻訳（iatf_knowledge は英語クエリ推奨だが既に安定）
    has_japanese = any('\u3000' <= c <= '\u9fff' for c in query)
    if not has_japanese or collection == "iatf_knowledge":
        return query
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": f"Translate this Japanese technical query to English (return only the translation, no explanation):\n{query}",
                "stream": False,
                "options": {"num_predict": 80}
            },
            timeout=15,
        )
        resp.raise_for_status()
        en_query = resp.json().get("response", "").strip()
        if en_query and len(en_query) > 3:
            logger.info(f"[rag] translated: '{query}' → '{en_query}'")
            return en_query
    except Exception as e:
        logger.warning(f"[rag] translation failed: {e}")
    return query

# rag_search() 内で呼び出す:
# vector, embed_ms = _embed(_translate_query(query, collection))
```

### 適用手順
1. `clawstack_mcp_server.py` に上記関数を追加
2. `rag_search()` 内の `_embed(query)` を `_embed(_translate_query(query, collection))` に変更
3. `docker cp` でコンテナに転送 → MCP サーバー再起動

---

## P4: Docling → ingest パイプライン強化

### 現状の問題
- `ingest_watchdog.py` は PyMuPDF + VLM でテキスト抽出
- PDF 構造（表・見出し・リスト）が失われてRAGスコアが低い

### 改善案: Docling を前処理として使う

```python
# ingest_watchdog.py に追加する関数

DOCLING_URL = os.getenv("DOCLING_URL", "http://docling:5001")

def extract_text_docling(pdf_path_or_url: str) -> str | None:
    """
    Docling で PDF を Markdown に変換して構造化テキストを取得。
    失敗時は None を返し、既存の PyMuPDF フォールバックへ。
    """
    try:
        resp = requests.post(
            f"{DOCLING_URL}/v1alpha/convert/source",
            json={"http_sources": [{"url": pdf_path_or_url}],
                  "options": {"to_formats": ["md"]}},
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        # Docling レスポンスから Markdown テキストを取得
        for doc in result.get("document", {}).get("export_results", []):
            if doc.get("format") == "md":
                return doc.get("content", "")
    except Exception as e:
        logger.warning(f"[ingest] Docling failed for {pdf_path_or_url}: {e}")
    return None

# 利用優先度:
# 1. Docling (構造化 Markdown) → 最高品質
# 2. PyMuPDF (プレーンテキスト) → 中品質
# 3. minicpm-v VLM (画像解析) → 低品質・最終手段
```

### 注意事項
- Docling は CPU重い処理 → タイムアウト 120秒 推奨
- Paperless 内部 URL から直接 PDF を取得できない場合は、先に `/tmp` に保存して from_path API を使う

---

## P5: ClickHouse TTL / データ保持設定

### 問題
ClickHouse のトレースデータが無期限に蓄積し、ディスクを逼迫する可能性がある。

### 修正: Langfuse の環境変数で TTL を設定

```yaml
# clawstack_v2/docker-compose.yml の langfuse / langfuse-worker に追加

environment:
  - LANGFUSE_DEFAULT_TTL_DAYS=90     # ← 追加: トレース保持期間 90日
  # ClickHouse TTL は Langfuse が自動設定する場合が多い
  # 手動設定が必要な場合は ClickHouse マイグレーションで ALTER TABLE ... TTL を実行
```

### Qdrant スナップショット（手動実行）
```bash
# 現時点の手動バックアップ方法
curl -X POST "http://localhost:6333/collections/universal_knowledge/snapshots"
curl -X POST "http://localhost:6333/collections/iatf_knowledge/snapshots"
# スナップショットは Qdrant コンテナ内 /qdrant/snapshots/ に保存される
```

---

## P6: Portal Hub KPI カード追加案

### 追加したいカード（現 observability_hub/index.html へ）

```javascript
// 追加カード定義

const NEW_CARDS = [
  {
    id: "kpiFallbackRate",
    label: "Fallback率 (直近20件)",
    target: "15%以下",
    color: "yellow",
    query: "litellm_logs_fallback_count / total"
  },
  {
    id: "kpiHarnessBlock",
    label: "ハーネス遮断回数 (本日)",
    target: "0件が理想",
    color: "purple",
    note: "Langfuse metadata.harness_action=blocked のトレース数"
  },
  {
    id: "kpiSelfHealSuccess",
    label: "Self-Heal 成功率",
    target: "60%以上",
    color: "green",
    query: "Langfuse score: self_heal_result"
  },
  {
    id: "kpiDocIngested",
    label: "今週の文書取り込み数",
    color: "blue",
    query: "ingest_watchdog_state.json の更新数"
  }
];
```

### 実装方針
- 既存の `index.html` に `NEW_CARDS` を追加する形で拡張
- Langfuse API から metadata フィルタで取得
- データ未取得の場合は `N/A` 表示（エラーにしない）

---

## P7: Qdrant スナップショット n8n ワークフロー

### 概要
毎日 02:00 JST に Qdrant の全コレクションをスナップショット取得する n8n ワークフロー。

### ワークフロー構成（JSON 骨格）

```json
{
  "name": "Qdrant Daily Snapshot",
  "nodes": [
    {
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": { "rule": { "interval": [{ "field": "cronExpression", "expression": "0 17 * * *" }] } }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Snapshot universal_knowledge",
      "parameters": {
        "method": "POST",
        "url": "http://qdrant:6333/collections/universal_knowledge/snapshots"
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Snapshot iatf_knowledge",
      "parameters": {
        "method": "POST",
        "url": "http://qdrant:6333/collections/iatf_knowledge/snapshots"
      }
    }
  ]
}
```

> **注意**: cron `0 17 * * *` は UTC 17:00 = JST 02:00

---

## env 差分案（.env への追加項目）

```bash
# === Langfuse / Observability ===
# 既存キーはそのまま。以下を追加:

LANGFUSE_DEFAULT_TTL_DAYS=90

# === RAG 品質改善 ===
# ingest_watchdog / clawstack_mcp_server が参照
DOCLING_URL=http://docling:5001
OLLAMA_URL=http://ollama:11434
RAG_TRANSLATE_ENABLED=true      # P3: 日→英自動補完の有効/無効フラグ

# === Tracing ===
# clawstack_tracing.py が参照（既に LANGFUSE_HOST 等は設定済み）
TRACING_ENABLED=true
```

---

## docker-compose 差分サマリー

対象ファイル: `clawstack_v2/docker-compose.yml`

```yaml
# langfuse に追加:
environment:
  - REDIS_AUTH=
  - LANGFUSE_DEFAULT_TTL_DAYS=90

# langfuse-worker に追加:
environment:
  - REDIS_AUTH=
  - LANGFUSE_DEFAULT_TTL_DAYS=90
```

---

## 実装順序推奨

```
Step 1: P1 (Redis auth修正) → compose 再起動 → ログ確認
Step 2: P2 (request_id追加) → tracing.py 更新 → cp + 再起動
Step 3: P3 (日→英翻訳) → mcp_server.py 更新 → cp + 再起動
Step 4: P5 (TTL設定) → compose 再起動
Step 5: P6 (Portal Hub カード) → index.html 更新
Step 6: P4 (Docling統合) → ingest_watchdog.py 更新 (慎重に)
Step 7: P7 (Qdrant snapshot) → n8n ワークフロー作成
```

---

## テスト計画

| テスト | 確認方法 |
|--------|---------|
| P1 Redis 警告消滅 | `docker logs langfuse-worker \| grep AUTH` がゼロ |
| P2 request_id 記録 | Langfuse UI でトレースの metadata に `request_id` が表示 |
| P3 翻訳補完 | `rag_search("公差解析のポイント")` でスコア 0.65+ |
| P4 Docling | ingest後のRAGスコアが VLM比で向上 |
| P5 TTL | ClickHouse で `SHOW CREATE TABLE traces` に TTL が設定される |
| P6 Portal Hub | `http://localhost:8088/apps/observability_hub/` で新カード表示 |
| P7 Snapshot | 翌朝 02:00 以降に Qdrant スナップショットファイルが存在 |

---

## ロールバック計画

| 変更 | ロールバック手順 |
|------|--------------|
| P1 Redis | `REDIS_AUTH=` 行を削除 → force-recreate |
| P2/P3 tracing/mcp | `git checkout` で元ファイルを復元 → `docker cp` → MCP 再起動 |
| P4 Docling | `extract_text_docling()` 呼び出しをコメントアウト → cp → 再起動 |
| P5 TTL | env から `LANGFUSE_DEFAULT_TTL_DAYS` を削除 → force-recreate |
| P6 Portal | `git checkout apps/observability_hub/index.html` |
| P7 Snapshot | n8n ワークフローを無効化 |

---

## 今回は実装しないが将来候補

| 項目 | 理由 / 条件 |
|------|-----------|
| OpenClaw 1リクエスト全体を親trace化 | OpenClaw 内部フックが必要 → OpenClaw 側の対応待ち |
| LangSmith 比較モード | 匿名化データ準備が必要 |
| GPU 追加 | ハードウェア投資判断 |
| Dify 廃止 / Node-RED 整理 | 段階的移行計画が必要 |
| PostgreSQL 自動バックアップ | pg_dump + n8n or cron で比較的容易 |
| Langfuse Prompt Management | トレースデータが蓄積後に有効活用 |
| RAG ハイブリッド検索 (BM25 + vector) | Qdrant v1.7+ で対応可能 |
