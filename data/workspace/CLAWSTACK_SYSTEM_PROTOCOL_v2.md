# Clawstack AI Engineering Platform — システムプロトコル v2.0
**作成日**: 2026-03-10
**前バージョン**: v1.0 (2026-03-09)
**対象**: ChatGPT / 外部LLMによるシステム評価用
**ホスト**: Windows 11 Pro, Docker Desktop, MiniPC (Intel N100 / RAM 32GB / NVMe 2TB)
**Compose プロジェクト名**: `clawstack-unified`

---

## 1. システム概要

Clawstack は、機械設計エンジニア（鈴木靖彦）が自社業務自動化のために構築した、**完全ローカル稼働・プライバシー優先のAIエンジニアリングプラットフォーム**。

### 設計哲学
- **無料OSS優先**: 有料クラウドAPIはフォールバックのみ（Gemini Flash無料枠）
- **Dockerコンテナ完結**: 40+コンテナが内部ネットワークで通信
- **AIエージェント中心**: OpenClaw が全サービスを自律制御
- **RAG**: 社内技術文書をベクトルDBに蓄積、質問時に自動検索
- **AIハーネス制御**: GCTMSフレームワーク（Guard/Context/Tool/Memory/Supervision）
- **LLMOps可観測性**: Langfuse v3 による全LLM呼び出しのトレーシング ← v2.0 新機能

### ハードウェア
```
CPU: Intel N100 (4コア)
RAM: 32GB
Storage: NVMe 2TB
GPU: なし（CPU推論のみ）
OS: Windows 11 Pro 26200
Docker: Desktop (WSL2バックエンド)
```

---

## 2. ネットワーク構成

```
外部 (ホスト:127.0.0.1)          内部 (Docker Network: clawstack-unified)
─────────────────────────────────────────────────────────────────────
:18789  ← OpenClaw Gateway       openclaw → litellm:4000 → Gemini/Ollama
:5679   ← n8n                    openclaw → qdrant:6333
:1880   ← Node-RED               openclaw → n8n:5678 (MCP経由)
:8088   ← Portal (nginx)         litellm → langfuse:3000 (トレース)
:8081   ← SearXNG                clawstack-mcp → infinity:7997 → qdrant
:8000   ← Paperless-ngx          langfuse → clickhouse:8123
:6333   ← Qdrant                 langfuse-worker → redis:6379 → clickhouse
:3001   ← Langfuse UI            ingest_watchdog → paperless → infinity → qdrant
:7870   ← WorkStudy AI           n8n → telegram (通知)
:8090   ← Quality Dashboard
:8087   ← Docling
:7997   ← Infinity (embed)
:9000/9001 ← MinIO (S3互換)
:5432   ← PostgreSQL
:6379   ← Redis
:11434  ← Ollama (Docker)
:50021  ← VoiceVox
:3100   ← MiniGame UI
:8100   ← MiniGame API
```

---

## 3. AIエージェント層（コア）

### 3-1. OpenClaw Gateway
| 項目 | 値 |
|-----|----|
| **役割** | メインAIエージェント。全サービスの自律制御・会話UI |
| **ベースモデル** | `google/gemini-2.5-flash` (primary) |
| **フォールバック** | `ollama/qwen2.5-coder:7b` |
| **外部ポート** | 18789 (Gateway), 18791 (Browser CDP) |
| **認証** | Bearer `yasu-fresh-token-2026-02-01` |
| **Browser** | Playwright Chromium (headless, CDP 18801) |
| **MCP servers** | `n8n-workflows`, `clawstack-tools` |

#### エージェント制御ファイル（コンテナ内 /home/node/clawd/）
| ファイル | 役割 |
|---------|------|
| `PORTAL_APPS.md` | 全アプリ使用方法・MCPツール使い方（コンテキスト） |
| `SOUL.md` | 17ルールの行動規範（自律制御憲法） |
| `PROMISES.md` | 21項目の約束事項・禁止事項・Human-in-the-Loop承認フロー |
| `TOOLS.md` | ツール詳細リファレンス |
| `clawstack_tracing.py` | Langfuse v3 トレーシングライブラリ |
| `clawstack_mcp_server.py` | MCP サーバー本体 |
| `ingest_watchdog.py` | Paperless→RAG 自動インジェストデーモン |
| `rag_search.py` | RAG検索CLIスクリプト |
| `workflow_healer.py` | n8n ワークフロー自己修復スクリプト |

### 3-2. LiteLLM Proxy (port 4000)
| 項目 | 値 |
|-----|----|
| **役割** | 複数LLMの統合管理、ルーティング、コスト計測 |
| **Primary** | `google/gemini-2.5-flash` via Google OpenAI互換API |
| **Fallback** | `openai/qwen2.5-coder:7b` via `http://ollama:11434/v1` |
| **Embedding** | `text-embedding-ada-002` → Ollama `nomic-embed-text` |
| **Callback** | `success_callback: ["langfuse"]` — 全呼び出しを自動トレース |

### 3-3. Clawstack MCP Server (port 9876) ← v2.0 新機能
| 項目 | 値 |
|-----|----|
| **役割** | OpenClaw から呼べる MCP ツール提供サーバー |
| **起動** | `python3 /home/node/clawd/clawstack_mcp_server.py` (entrypoint.shで自動起動) |
| **Transport** | FastMCP streamable-http (`http://127.0.0.1:9876/mcp`) |
| **ツール1** | `rag_search(query, collection, top_k)` — Infinity embed → Qdrant検索 |
| **ツール2** | `web_search(query, num_results, engines)` — SearXNG経由Web検索 |
| **Tracing** | 各ツール呼び出しを Langfuse span で記録 |

#### MCPサーバー利用例（OpenClawから）
```
mcp__clawstack-tools__rag_search(query="CETOL 6sigma tolerance stackup", collection="universal_knowledge", top_k=5)
mcp__clawstack-tools__web_search(query="IATF 16949 revision 2024", num_results=5)
```

---

## 4. LLMOps 可観測性層 ← v2.0 新規実装

### 4-1. アーキテクチャ
```
OpenClaw (LLM呼び出し)
    │
    ▼
LiteLLM Proxy ──── success_callback ────► Langfuse Web (port 3001)
                                               │
MCP Tools (RAG/Web)                           │ store via OTLP + ingestion API
    │                                          ▼
    ├── clawstack_tracing.py ──────────► MinIO (langfuse-events bucket)
    │   span_rag / span_web_search             │
    │                                          ▼
    └── Langfuse SDK v3                   langfuse-worker
        (span + score 記録)                    │ BullMQ (Redis)
                                               │
                                               ▼
                                          ClickHouse (クエリDB)
                                               │
                                               ▼
                                          REST API → Portal Hub
```

### 4-2. Langfuse v3 セットアップ
| 項目 | 値 |
|-----|----|
| **Server** | `langfuse/langfuse:3.37.0` (port 3001) |
| **Worker** | `langfuse/langfuse-worker:3.37.0` ← v2.0 追加 |
| **ClickHouse** | `clickhouse/clickhouse-server:24.8` (named volume) |
| **DB** | PostgreSQL `langfuse` データベース |
| **Events Storage** | MinIO `langfuse-events` バケット |
| **Public Key** | `pk-lf-07926c92-5480-4fb5-ae97-39e35a0a0ce5` |
| **Host (internal)** | `http://langfuse:3000` |
| **UI** | `http://localhost:3001` |
| **Account** | `admin@clawstack.local` / `Clawstack2026!` |
| **Organization** | "Clawstack" / Project: "clawstack-prod" |

### 4-3. 計測されるメトリクス
| メトリクス | 計測元 | 記録先 |
|-----------|--------|--------|
| LLM応答レイテンシ | LiteLLM callback | Langfuse trace |
| LLMコスト (USD) | LiteLLM callback | Langfuse trace |
| RAG関連性スコア | clawstack_tracing.py | Langfuse score `rag_relevance` |
| MCP tool 実行時間 | clawstack_tracing.py | Langfuse span metadata |
| Web検索レイテンシ | clawstack_tracing.py | Langfuse span metadata |

### 4-4. Portal 可観測性Hub
- **URL**: `http://localhost:8088/apps/observability_hub/`
- **機能**: サービス死活監視・RAGスコア・LLMコスト・最新トレース一覧
- **自動更新**: 30秒ごと
- **ベンチマーク**: `docs/rag_benchmark.json` に期待スコア定義

---

## 5. RAG / ナレッジ管理層

### 5-1. Qdrant ベクトルDB (port 6333)
| コレクション | 次元数 | Embedモデル | 内容 | ポイント数 |
|------------|--------|------------|------|----------|
| `universal_knowledge` | 1024 | mxbai-embed-large-v1 (Infinity) | FMEA/5Why/CETOL/FEM書籍 + Paperless全文書 | 1,700+ |
| `iatf_knowledge` | 768 | nomic-embed-text (Ollama) | IATF 16949 文書 | 99 |

### 5-2. Infinity Embedding Server (port 7997)
- **モデル**: `mxbai-embed-large-v1` (1024次元)
- **用途**: RAGインジェスト・MCP RAG検索時のクエリベクトル化

### 5-3. Paperless-ngx (port 8000) + Ingest Watchdog
```
Paperless (OCR済み文書) ──► ingest_watchdog.py (5分ごとポーリング)
                                    │
                    ┌───────────────┤
                    │ OCR text ≥80文字: PyMuPDF直接抽出
                    │ OCR text <80文字: minicpm-v VLM (画像解釈)
                    └───────────────┤
                                    ▼
                            Infinity embed
                                    ▼
                            Qdrant universal_knowledge
```

**インジェスト状態**: `ingest_watchdog_state.json` で処理済みIDを管理

### 5-4. RAGクエリ品質ガイド
| ドキュメント種別 | 推奨クエリ言語 |
|---------------|--------------|
| CETOL/FEM | **英語** (VLM画像説明で取り込まれているため) |
| FMEA/5Why | 日本語・英語どちらも可 |
| IATF 16949 | 英語推奨 (`iatf_knowledge` collection) |

---

## 6. ワークフロー自動化層

### 6-1. n8n (port 5679)
| 項目 | 値 |
|-----|----|
| **MCP endpoint** | `http://n8n:5678/mcp-server/http` |
| **MCP tools** | `search_workflows`, `execute_workflow`, `get_workflow_details` |
| **主要ワークフロー** | 下表参照 |

#### アクティブワークフロー
| ID | 名前 | 役割 |
|----|------|------|
| `jVGXe2GEIz6RN7Z0` | Ingest Watchdog Supervisor | Watchdogデーモン監視・5分ごとチェック |
| `vc0kATBeDoQxKgPY` | P017 Workflow Self-Healer | 全n8nワークフロー障害を自動修復・15分ごと |

#### Self-Healer 修復戦略
```
エラー検出 → restart×2 → LLM修正(qwen2.5-coder:7b)×2 → Telegram エスカレート
```

### 6-2. Node-RED (port 1880)
- IoT/データフロー用。現在はスタンバイ状態。

---

## 7. ローカルLLM層

### 7-1. Docker Ollama (内部 http://ollama:11434)
| モデル | 用途 |
|--------|------|
| `qwen2.5-coder:7b` | LiteLLM fallback・コード修正 |
| `deepseek-r1:7b` | 推論・思考チェーン |
| `deepseek-r1:14b` | 高精度推論 |
| `minicpm-v` | VLM画像解析（インジェスト用） |
| `nomic-embed-text` | IATF知識ベースembedding |
| `llava` | 補助VLM |

> **注意**: Native Windows Ollama (port 11434) と Docker Ollama (内部ネット) の2系統が存在。OpenClawはDockerOllamaを使用。

### 7-2. Gemini API
- **モデル**: `gemini-2.5-flash` (Google OpenAI互換API経由)
- **APIキー**: `.env` の `GEMINI_API_KEY`
- **LiteLLM設定**: `openai/gemini-2.5-flash` → `https://generativelanguage.googleapis.com/v1beta/openai`

---

## 8. 文書管理・解析層

### 8-1. Paperless-ngx (port 8000)
- OCR付き文書管理。全取り込み文書がRAGへ自動インジェスト。

### 8-2. Docling (port 8087)
- **役割**: PDF/DOCX/PPTXをMarkdown変換（RAG前処理）
- **API**: `POST /v1alpha/convert/source`

### 8-3. Dify (port 3000 / internal)
- LLMアプリ構築プラットフォーム。スタンバイ状態。

---

## 9. 専門アプリ層

### 9-1. WorkStudy AI (port 7870)
- 動画から作業動作を解析、MOST分析を実施するAIアプリ

### 9-2. Quality Dashboard (port 8090)
- Streamlit製。品質データの可視化ダッシュボード。

### 9-3. DXF→3D アプリ (port 8003)
- DXFファイルからCSG 3D形状を生成。manifold3dエンジン使用。
- Qwen3:8b による AI自己チェック付き。

### 9-4. Local HTML Apps (Portal経由 port 8088)
| アプリ | URL |
|--------|-----|
| Observability Hub | `/apps/observability_hub/` ← v2.0新追加 |
| Tolerance Center | `/apps/tolerance_hub/` |
| Injection Molding Hub | `/apps/molding_hub/` |
| Kinematics Hub | `/apps/kinematics_hub/` |
| OpenRadioss Hub | `/apps/radioss_hub/` |

---

## 10. インフラ層

### 10-1. PostgreSQL (port 5432)
- n8n, Langfuse, Paperless, Open WebUI の永続データ

### 10-2. Redis (port 6379)
- n8n キャッシュ, Langfuse BullMQ ジョブキュー (ノーパスワード設定)

### 10-3. MinIO (port 9000/9001)
- S3互換オブジェクトストレージ
- バケット: `langfuse-events` (Langfuseイベント一時保管)

### 10-4. ClickHouse (port 8123 / internal only)
- Langfuse v3 のトレースデータを格納・集計するOLAPエンジン

### 10-5. SearXNG (port 8081)
- プライベートWebメタ検索エンジン。MCP web_search ツールのバックエンド。

### 10-6. VoiceVox (port 50021)
- ローカル音声合成エンジン（日本語TTS）

---

## 11. AIハーネス制御フレームワーク (GCTMS)

```
G - Guard    : 操作承認フロー (P021) / 禁止操作リスト
C - Context  : PORTAL_APPS.md + TOOLS.md = 常時コンテキスト
T - Tool     : MCP tools / n8n / RAG / exec
M - Memory   : Qdrant RAG + OpenClaw Memory (litellm embedding)
S - Supervision: SOUL.md Rule 17 (構造化報告) + n8n Self-Healer
```

### Human-in-the-Loop 承認フロー (P021)
| レベル | 対象操作 |
|--------|---------|
| 自動実行 | ログ閲覧・情報検索・ステータス確認・読み取り専用操作 |
| 要承認 (Telegram) | 依存パッケージ更新・docker-compose変更・外部書き込み・n8n変更 |
| 禁止 | 本番DB削除・認証情報外部送信・`--no-cache`ビルド |

---

## 12. データフロー全体図

```
[ユーザー/Telegram]
        │
        ▼
[OpenClaw Gateway] ←→ [Claude Code / Clawdbot]
        │
   ┌────┴─────────────────────────────────────────┐
   │                                               │
   ▼                                               ▼
[LiteLLM Proxy]                          [MCP: clawstack-tools]
   │   │                                     │         │
   │   └──► [Langfuse] (トレース)           [RAG]    [WebSearch]
   │              │                            │         │
   ▼              ▼                            ▼         ▼
[Gemini/Ollama] [ClickHouse]            [Infinity]  [SearXNG]
                                              │
                                              ▼
                                          [Qdrant]
                                              ▲
                                              │ (自動インジェスト)
                                    [Paperless] + [Docling]
                                              ▲
                                              │
                                        [社内文書PDF]

[n8n Workflows]
   ├── Ingest Watchdog Supervisor (5分ごと監視)
   ├── P017 Self-Healer (15分ごとワークフロー修復)
   └── Telegram通知
```

---

## 13. セキュリティ設定

- 全サービスは `127.0.0.1` バインド（LAN非公開）
- 認証トークン: OpenClaw Bearer token
- n8n MCP: JWT認証
- Langfuse: Basic認証 (pk/sk)
- `.env` に APIキー集約（Git管理対象外）

---

## 14. 既知の課題・制限事項

| 課題 | 影響 | 対応状況 |
|------|------|---------|
| Redis auth 警告 | Langfuse/n8n がRedisにパスワード送信するが設定なし | 軽微・動作に影響なし |
| CETOL6/FEM RAGスコア低 | VLM画像説明でインジェストのため英語クエリが必要 | 回避策：英語クエリ推奨 |
| GPU なし | 大型モデルの推論が遅い | CPU only 割り切り |
| Langfuse SDK互換 | v3 SDK の auth_check() がpydantic validation error | トレース送信には影響なし |

---

## 15. v1.0 → v2.0 変更サマリー

| 変更内容 | 詳細 |
|---------|------|
| **Langfuse Worker 追加** | `langfuse-worker:3.37.0` コンテナ。MinIO→ClickHouse処理 |
| **MCP Server 実装** | `clawstack_mcp_server.py` (FastMCP, port 9876) — RAG+Web検索ツール |
| **Tracing ライブラリ** | `clawstack_tracing.py` — Langfuse v3 span/score記録 |
| **Portal 可観測性Hub** | `apps/observability_hub/index.html` — リアルタイムKPIダッシュボード |
| **RAGベンチマーク定義** | `docs/rag_benchmark.json` — 5クエリの期待スコア |
| **LiteLLM → Langfuse** | `success_callback: ["langfuse"]` — 全LLM呼び出しを自動記録 |
| **Langfuse セットアップ完了** | アカウント・組織・プロジェクト・APIキー取得済み |
| **トレース確認済み** | Langfuse UIに4件トレース記録を確認 |
| **SOUL.md 更新** | Rule 16 (進捗報告) / Rule 17 (構造化報告) 追加 |
| **PROMISES.md 更新** | P021 Human-in-the-Loop 承認フロー追加 |
| **entrypoint.sh 更新** | mcp/langfuse 自動インストール + MCPサーバー自動起動 |

---

## 16. 評価依頼ポイント（ChatGPT向け）

1. **MCPの活用度**: clawstack-tools MCP (RAG + Web検索) と n8n MCP の組み合わせは最適か？
2. **トレーシングの有効性**: LiteLLM callback + カスタムspan の設計は適切か？
3. **RAG品質向上策**: VLM画像説明ベースのインジェスト問題を根本解決する方法は？
4. **アーキテクチャの冗長性**: 重複機能・排除すべきコンポーネントはあるか？
5. **GPU不在でのモデル選定**: N100 CPUで最大効率を出すモデル構成は？
6. **Self-Healer の信頼性**: n8n → Docker exec → LLM修正 の自己修復ループは堅牢か？
