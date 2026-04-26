# LightRAG PoC 設計書
> Clawstack Unified — グラフRAG補助層 / 制定: 2026-04-17

---

## 1. 採用背景と位置づけ

Graphify プロトコル（`graphify_complete_protocol_utf8.zip`）が想定していた
「グラフRAG補助層」の実装ツールとして **LightRAG (HKUDS/LightRAG)** を採用する。

| 比較点 | Microsoft GraphRAG | **LightRAG** ← 採用 |
|---|---|---|
| Docker REST API | なし（CLI のみ） | あり (FastAPI) |
| Qdrant 統合 | なし | あり（ネイティブ対応） |
| Ollama 互換インタフェース | なし | あり |
| コミュニティ検出 | Leiden（重い） | 階層的グラフ（軽量） |
| 導入コスト | 高 | 低 |
| ライセンス | MIT | MIT |

**LightRAG の役割**: Qdrant（ベクトル検索）の前段に置くグラフ構造検索層。
Qdrant を置き換えるのではなく、**横付けで共存**させる。

```
クエリ
  ↓
LightRAG グラフ検索（関係・コミュニティ）
  ↓ 信頼度が低い場合
Qdrant ベクトル検索（フォールバック）
  ↓
原本 PDF / DB 参照
  ↓
最終回答
```

---

## 2. コンテナ構成

ファイル: `docker-compose.lightrag.yml`

```
lightrag コンテナ
  ポート:  127.0.0.1:18795 → 9621
  LLM:    LiteLLM proxy → google/gemini-2.5-flash
  Embed:  Infinity (http://infinity:7997) → mxbai-embed-large-v1 (1024-dim)
  Vector: Qdrant (http://qdrant:6333) → コレクション: lightrag_knowledge
  Data:   ./lightrag/data/    (グラフデータ・KV)
  Inbox:  ./lightrag/inbox/   (取込待ちファイル)
```

起動コマンド:
```bash
docker compose -f docker-compose.yml -f docker-compose.lightrag.yml up -d lightrag
```

---

## 3. Phase 0 — 前提確認（今すぐ実施可能）

### チェックリスト
```bash
# 3-1. イメージ pull 確認
docker pull hkuds/lightrag:latest

# 3-2. ポート競合確認
netstat -ano | grep 18795

# 3-3. 既存サービス稼働確認
curl -s http://localhost:6333/collections | python -m json.tool  # Qdrant
curl -s http://localhost:7997/health                              # Infinity
curl -s http://localhost:4000/health                              # LiteLLM

# 3-4. バックアップ（lightrag はデータをローカルに書くので事前不要だが
#      既存 Qdrant コレクションを念のためスナップショット）
curl -X POST http://localhost:6333/collections/universal_knowledge/snapshots
```

### 合格基準
- `hkuds/lightrag:latest` が pull できる
- ポート 18795 が空いている
- Qdrant / Infinity / LiteLLM が全て応答する

---

## 4. Phase 1 — 読み取り専用 PoC

### 対象ドキュメント（優先度 A）
1. Paperless から IATF 文書 5 件
2. 不具合報告書サンプル 5 件
3. 品質手順書サンプル 5 件

### 手順

#### 4-1. LightRAG 起動
```bash
docker compose -f docker-compose.yml -f docker-compose.lightrag.yml up -d lightrag
docker compose logs -f lightrag  # ログ確認
curl http://localhost:18795/health
```

#### 4-2. ドキュメント投入
```bash
# PDF ファイルを inbox に配置してからスキャン
cp /path/to/iatf_doc.pdf lightrag/inbox/
curl -X POST http://localhost:18795/documents/scan \
  -H "Content-Type: application/json" \
  -d '{"scan_path": "/app/inbox"}'

# またはファイルを直接アップロード
curl -X POST http://localhost:18795/documents/upload \
  -F "file=@/path/to/document.pdf"
```

#### 4-3. グラフ確認
```bash
# ノード一覧取得
curl http://localhost:18795/graph/label/list

# クエリ実行（ハイブリッドモード推奨）
curl -X POST http://localhost:18795/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "IATF 10.2 に関係する不具合と是正処置は何か",
    "mode": "hybrid"
  }'
```

### 評価基準
| 指標 | 合格ライン |
|---|---|
| 主要キーワード到達率 | Qdrant 単独より改善 |
| 重複ノード率 | 5% 未満 |
| レスポンス時間（hybrid） | 30秒以内 |
| ノイズ関係数 | 人手評価で許容範囲 |

---

## 5. Phase 2 — 差分更新（Phase 1 合格後）

- 新規文書のみ再処理（ハッシュ重複チェック）
- 既存ノードの統合ルール策定
- n8n ワークフロー連携（Paperless 取込時に自動グラフ化）

n8n ワークフロー概要:
```
Paperless Webhook (新規文書登録)
  → ハッシュ重複チェック
  → LightRAG /documents/upload
  → 成功: PostgreSQL に索引登録
  → 失敗: 再試行 x3 → エラーキュー
```

---

## 6. Phase 3 — OpenClaw 連携（Phase 2 合格後）

`data/workspace/graph_search.py` を追加し、OpenClaw の検索前段に組み込む。

```python
# graph_search.py の概要（Phase 3 で実装）
import httpx

LIGHTRAG_URL = "http://lightrag:9621"  # Docker 内部アドレス

def graph_search(query: str, mode: str = "hybrid") -> dict:
    """LightRAG にクエリし、構造化結果を返す"""
    resp = httpx.post(f"{LIGHTRAG_URL}/query", json={"query": query, "mode": mode})
    resp.raise_for_status()
    return resp.json()

def search_with_fallback(query: str) -> dict:
    """LightRAG → Qdrant フォールバック付き検索"""
    try:
        result = graph_search(query)
        if result.get("confidence", 0) >= 0.7:
            return {"source": "lightrag", "data": result}
    except Exception:
        pass
    # フォールバック: Qdrant
    from search_qdrant import search as qdrant_search
    return {"source": "qdrant", "data": qdrant_search(query)}
```

---

## 7. ロールバック手順

```bash
# LightRAG のみ停止（既存サービスに影響なし）
docker compose -f docker-compose.yml -f docker-compose.lightrag.yml stop lightrag
docker compose -f docker-compose.yml -f docker-compose.lightrag.yml rm -f lightrag

# Qdrant の lightrag_knowledge コレクションを削除（必要な場合のみ）
curl -X DELETE http://localhost:6333/collections/lightrag_knowledge

# ローカルデータ削除（必要な場合のみ）
rm -rf lightrag/data lightrag/inbox lightrag/logs
```

---

## 8. 運用ルール（Graphify プロトコル準拠）

| ルール | 内容 |
|---|---|
| 正本の扱い | LightRAG ノードは補助データ。原本 PDF / DB が正本 |
| 承認フロー | AI抽出 → draft → 担当確認 → reviewed → 業務利用 → approved |
| 外部公開 | 127.0.0.1 バインド限定。外部公開禁止 |
| 機密文書 | 社外秘文書を LightRAG に投入する際は部門長承認 |
| バックアップ | `lightrag/data/` を定期バックアップ（既存 Qdrant バックアップに追加） |

---

## 9. 今後の発展オプション

| オプション | 内容 | 優先度 |
|---|---|---|
| Neo4j 移行 | Phase 2 以降で NetworkX → Neo4j へ | 低（必要になってから） |
| PostgreSQL KV | KV ストアを PostgreSQL に移行 | 低 |
| Portal カード | Portal に LightRAG ヘルス + ノード統計カード追加 | 中 |
| 承認待ちキュー | 未承認ノードの人手レビュー UI | 中（Phase 3 以降） |
