# Clawstack AI Engineering Platform — システムプロトコル v1.0
**作成日**: 2026-03-09
**対象**: ChatGPT / 外部LLMによるシステム評価用
**ホスト**: Windows 11 Pro, Docker Desktop, MiniPC (Intel N100 / RAM 32GB)
**Compose プロジェクト名**: `clawstack-unified`

---

## 1. システム概要

Clawstack は、機械設計エンジニア（鈴木靖彦 / y.suzuki.hk@gmail.com）が自社業務自動化のために構築した、**完全ローカル稼働・プライバシー優先のAIエンジニアリングプラットフォーム**である。

### 設計哲学
- **無料OSS優先**: 有料クラウドAPIはフォールバックのみ
- **Dockerコンテナ完結**: すべてのサービスが内部Dockerネットワークで通信
- **AIエージェント中心**: OpenClaw が全サービスを自律制御
- **RAG（検索拡張生成）**: 社内技術文書をベクトルDBに蓄積、質問時に自動検索
- **AIハーネス制御**: エージェントの暴走を防ぐGCTMSフレームワーク実装

---

## 2. ネットワーク構成

### 内部Dockerネットワーク
全コンテナは `clawstack-unified` という同一ネットワーク内に属し、**サービス名でDNS解決**される。

```
例: http://qdrant:6333, http://ollama:11434, http://n8n:5678
```

### 外部アクセス（ホスト側）
すべて `127.0.0.1` にバインド（LAN非公開）。Nginx リバースプロキシは使用せず。

---

## 3. AIエージェント層（コア）

### 3-1. OpenClaw Gateway (clawdbot-gateway)
| 項目 | 値 |
|-----|----|
| **役割** | メインAIエージェント。全サービスの自律制御・会話インターフェース |
| **ベースモデル** | Google Gemini 2.5 Flash (claude-sonnet-4-6 based OpenClaw v2026.3.2) |
| **外部ポート** | 18789 (Gateway API), 18791 (Browser CDP) |
| **認証トークン** | `yasu-fresh-token-2026-02-01` |
| **コンテキストファイル** | `/home/node/clawd/PORTAL_APPS.md` (起動時ロード) |
| **ブラウザ** | Playwright Chromium (headless, CDP port 18801) |

#### マウントされたコンテキストファイル群
| ファイル | 役割 |
|---------|------|
| `SOUL.md` | エージェントのペルソナ・Prime Directives・17の運用ルール |
| `PROMISES.md` | ユーザーとの約束事項 (P001〜P021)・承認フロー |
| `PORTAL_APPS.md` | 全アプリの操作方法・MCPツール使用法（メインコンテキスト） |
| `TOOLS.md` | RAG検索・Web検索・Langfuse の簡易チートシート |

#### 環境変数（内部サービスURL）
```
QDRANT_URL=http://qdrant:6333
OLLAMA_URL=http://ollama:11434
LITELLM_URL=http://litellm:4000
INFINITY_URL=http://infinity:7997
SEARXNG_URL=http://searxng:8080
MINIO_URL=http://minio:9000
N8N_API_URL=http://n8n:5678/api/v1
PAPERLESS_API_URL=http://paperless:8000/api
OPENAI_BASE_URL=http://litellm:4000/v1  ← OpenClawのメモリ機能はLiteLLM経由
```

#### 自動起動プロセス（entrypoint.sh）
1. `paired.json` の保護（デバイスペアリング維持）
2. `openclaw` npm パッケージを最新版に自動更新
3. Playwright Chromium の共有ライブラリを確認・インストール
4. `ingest_watchdog.py` をバックグラウンド起動（Paperless → Qdrant自動取り込み）
5. **`clawstack_mcp_server.py` をバックグラウンド起動（MCP HTTPサーバー port 9876）**
6. Ollama プロキシ（ollama_proxy.js）を起動

---

### 3-2. MCP（Model Context Protocol）接続

OpenClaw は以下の2つのMCPサーバーに接続（`~/.claude.json` に設定済み）:

#### MCP Server 1: n8n-workflows
```json
{
  "type": "http",
  "url": "http://n8n:5678/mcp-server/http",
  "headers": {"Authorization": "Bearer <JWT>"}
}
```
**提供ツール**:
- `mcp__n8n-workflows__search_workflows` — n8nワークフロー検索
- `mcp__n8n-workflows__execute_workflow` — ワークフロー実行
- `mcp__n8n-workflows__get_workflow_details` — 詳細取得

#### MCP Server 2: clawstack-tools（新規追加 2026-03-09）
```json
{
  "type": "http",
  "url": "http://127.0.0.1:9876/mcp"
}
```
**スクリプト**: `/home/node/clawd/clawstack_mcp_server.py` (FastMCP 1.26.0 / streamable-http)
**提供ツール**:
- `mcp__clawstack-tools__rag_search(query, collection, top_k)` — Qdrant ベクトルDB検索（Infinity embed経由）
- `mcp__clawstack-tools__web_search(query, num_results, engines)` — SearXNG Web検索

---

## 4. LLM基盤

### 4-1. LiteLLM Gateway（LLMプロキシ）
| 項目 | 値 |
|-----|----|
| **役割** | 複数LLMプロバイダを統合。OpenAI互換API |
| **内部URL** | `http://litellm:4000/v1` |
| **外部ポート** | 4000 |
| **設定ファイル** | `data/state/litellm_config.yaml` |

#### 登録モデル
| モデル名 | バックエンド | 用途 |
|---------|------------|------|
| `google/gemini-2.5-flash` | Gemini API（OpenAI互換エンドポイント） | 通常会話・高品質（Primary） |
| `gemini/gemini-2.5-flash` | 同上 | エイリアス |
| `groq/llama-3.3-70b-versatile` | Groq API | ツール呼び出し・高速 |
| `groq/llama-3.1-8b-instant` | Groq API | 軽量・超高速 |
| `cerebras/llama3.1-70b` | Cerebras API | 超高速推論 |
| `ollama/deepseek-r1:14b` | Docker Ollama | オフライン・ローカル推論専用 |
| `text-embedding-ada-002` (他) | Ollama nomic-embed-text | 埋め込み（OpenClaw memory用） |
| `mixedbread-ai/mxbai-embed-large-v1` | Infinity (http://infinity:7997) | 高精度埋め込み（RAG用） |

#### Langfuse トレーシング（2026-03-09 接続済み）
```yaml
litellm_settings:
  success_callback: ["langfuse"]
  failure_callback: ["langfuse"]
environment_variables:
  LANGFUSE_PUBLIC_KEY: "pk-lf-clawstack-2026"
  LANGFUSE_SECRET_KEY: "sk-lf-clawstack-2026"
  LANGFUSE_HOST: "http://langfuse:3000"
```
LiteLLM経由の**全LLM呼び出しがLangfuseに自動記録**される。

### 4-2. Ollama（ローカルLLMサーバー）
| 項目 | 値 |
|-----|----|
| **役割** | ローカルLLM推論（インターネット不要） |
| **内部URL** | `http://ollama:11434` |
| **外部ポート** | 11434 |

**搭載モデル（Docker Ollama）**:
- `deepseek-r1:7b`, `deepseek-r1:14b` — 推論特化（ツール非対応）
- `llava:latest` — 画像認識VLM
- `minicpm-v:latest` — 軽量VLM（図解・グラフ認識、RAGインジェスト用）
- `nomic-embed-text:latest` — 埋め込み（768次元）
- `qwen2.5-coder:7b` — コード生成（ツール対応）

> **注意**: ホストOS（Windows）にも別途 Native Ollama が存在（PID ~5744、port 11434）。
> Docker内からは `http://ollama:11434` がDockerコンテナのOllama。
> `localhost:11434` はNative Ollamaにルーティングされる（競合注意）。

### 4-3. Infinity 埋め込みサーバー
| 項目 | 値 |
|-----|----|
| **役割** | 高精度テキスト埋め込み生成 |
| **内部URL** | `http://infinity:7997` |
| **外部ポート** | 7997 |
| **モデル** | `mixedbread-ai/mxbai-embed-large-v1`（1024次元） |
| **用途** | RAGインジェスト・クエリ埋め込み・OpenClaw memory |

### 4-4. llama.cpp Server（profile=llm、オプション）
| 項目 | 値 |
|-----|----|
| **役割** | GGUF形式モデルの直接推論（OpenAI互換API） |
| **外部ポート** | 8086 |
| **起動方法** | `docker compose --profile llm up -d llama_cpp` |
| **モデル配置** | `clawstack_v2/data/llama_cpp/models/model.gguf` |

---

## 5. ベクトルDB・RAGシステム

### 5-1. Qdrant（ベクトルDB）
| 項目 | 値 |
|-----|----|
| **役割** | セマンティック検索エンジン（RAGの心臓部） |
| **内部URL** | `http://qdrant:6333` |
| **外部ポート** | 6333 |
| **ストレージ** | `clawstack_v2/data/qdrant/` |

#### コレクション
| コレクション名 | 次元数 | 内容 | 埋め込みモデル |
|--------------|--------|------|------------|
| `universal_knowledge` | 1024 | FMEA/5Why/CETOL6σ/FEM書籍/Paperless全文書 | mxbai-embed-large-v1 (Infinity) |
| `iatf_knowledge` | 768 | IATF 16949 / TS 16949 品質マネジメント | nomic-embed-text (Ollama) |

### 5-2. RAGインジェストパイプライン

#### パイプライン1: Paperless → Qdrant（常時稼働）
```
Paperless NGX（文書管理）
  ↓ API（Token認証）
ingest_watchdog.py（gateway内で常時稼働）
  ↓ テキスト抽出 + minicpm-v VLM（画像多ページ）
Infinity embed（mxbai-embed-large-v1）
  ↓ 1024次元ベクトル
Qdrant universal_knowledge
```
- **スクリプト**: `/home/node/clawd/ingest_watchdog.py`
- **監視**: n8n ワークフロー（jVGXe2GEIz6RN7Z0 / "Ingest Watchdog Supervisor"）が5分ごとにプロセス確認・再起動
- **ステートファイル**: `/home/node/clawd/ingest_watchdog_state.json`（重複処理防止）
- **Paperless APIトークン**: `a451ceb5c13ac270faf3936405d207e4093ff580`

#### パイプライン2: CETOL6σ / FEM PDF → Qdrant（ハイブリッドOCR+VLM）
```
PDF（スキャン画像、テキスト層なし）
  ↓ PyMuPDF（ページを PNG に変換 / DPI=200）
  ↓ Tesseract OCR（jpn+eng）← テキスト多ページ（≥80文字）
  ↓ minicpm-v VLM（timeout=300s） ← グラフ・図解ページ（<80文字）
Infinity embed
  ↓
Qdrant universal_knowledge
```
- **スクリプト**: `/home/node/clawd/ingest_cetol_fem_docling.py`（現在バックグラウンド実行中）
- **対象**: `/home/node/clawd/paperless_consume/cetol6sigma/` + `fem_cae/`
- **VLMプロンプト**: 機械設計・公差解析・FEM専門の日本語説明（"The image shows"防止）
- **チャンクサイズ**: 900文字、オーバーラップ150文字

#### パイプライン3: Eメール → Qdrant
- **スクリプト**: `/home/node/clawd/ingest_eml_to_qdrant.py`（常時稼働中）

### 5-3. RAG検索（エージェント使用方法）
```bash
# MCPツール（推奨）
mcp__clawstack-tools__rag_search(query="CETOL 6sigma tolerance stackup", collection="universal_knowledge")

# フォールバック（exec）
python3 /home/node/clawd/rag_search.py "CETOL 6sigma tolerance stackup" --top 5
python3 /home/node/clawd/rag_search.py "内部監査 要求事項" --collection iatf_knowledge
```
**重要**: CETOL6σ・FEM文書は英語クエリ必須（日本語クエリのみでは低スコア）

---

## 6. ワークフロー自動化

### 6-1. n8n Automation
| 項目 | 値 |
|-----|----|
| **役割** | ノーコードワークフロー・Webhook・外部API連携 |
| **外部ポート** | 5679 |
| **内部ポート** | 5678 |
| **Admin** | y.suzuki.hk@gmail.com / clawstack2026 |
| **REST API Key** | `n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9` |
| **MCP Server** | `http://n8n:5678/mcp-server/http`（n8n-nodes-mcp v0.1.37） |
| **DB** | SQLite（`/root/.n8n/database.sqlite`） |
| **Dockerソケット** | `/var/run/docker.sock` マウント（docker CLI経由でgatewayコンテナを操作） |

**稼働中ワークフロー**:
| ID | 名前 | 概要 |
|----|------|------|
| `jVGXe2GEIz6RN7Z0` | Ingest Watchdog Supervisor | 5分毎にwatchdogプロセス確認・Telegram通知 |
| `vc0kATBeDoQxKgPY` | P017 Workflow Self-Healer | 15分毎に全ワークフロー健全性確認・LLM自己修復 |

**有効ノード設定**:
```
NODES_EXCLUDE=[]  ← Execute Command ノード有効
N8N_COMMUNITY_PACKAGES_ENABLED=true  ← コミュニティノード有効
user: root  ← Docker Socket 常時アクセス可
```

### 6-2. Node-RED (IoT/フロー制御)
| 項目 | 値 |
|-----|----|
| **役割** | MQTT・センサーデータ処理・産業IoT |
| **外部ポート** | 1880 |
| **MQTT連携** | Mosquitto (port 1883/9001) |

### 6-3. Mosquitto (MQTTブローカー、profile=tools)
- **外部ポート**: 1883 (TCP), 9001 (WebSocket)
- 匿名接続許可（開発環境設定）

---

## 7. 文書管理・ナレッジ

### 7-1. Paperless NGX（文書管理）
| 項目 | 値 |
|-----|----|
| **役割** | PDF・文書のOCR・タグ付け・検索・格納 |
| **外部ポート** | 8000 |
| **Admin** | admin / admin |
| **APIトークン** | `a451ceb5c13ac270faf3936405d207e4093ff580` |
| **消費ディレクトリ** | `clawstack_v2/data/paperless/consume/`（サブディレクトリがタグになる） |
| **DB** | PostgreSQL |
| **キュー** | Redis |
| **ingest自動化** | `ingest_watchdog.py` がAPIで全文書を取得 → Qdrant に投入 |

### 7-2. Open Notebook（NotebookLM クローン）
| 項目 | 値 |
|-----|----|
| **役割** | ローカル版NotebookLM。文書アップロード→Q&A・ポッドキャスト生成 |
| **外部ポート（UI）** | 8502 |
| **外部ポート（API）** | 5055 |
| **DB** | SurrealDB v2 (port 8001) |
| **LLM** | Ollama (http://ollama:11434) |

### 7-3. Docling（文書パーサー）
| 項目 | 値 |
|-----|----|
| **役割** | PDF/DOCX/PPTXをMarkdown/JSONに変換 |
| **外部ポート** | 8087 |
| **内部URL** | `http://docling:5001` |
| **API** | `POST /v1alpha/convert/source` |
| **注意** | 大容量スキャンPDF（6.8MB+）でOOMクラッシュ実績あり → 該当ファイルはTesseract OCRに切り替え |

### 7-4. Stirling PDF (profile=content)
- PDF結合・分割・OCR・変換
- 外部ポート: 8085

---

## 8. 可観測性・監視

### 8-1. Langfuse（LLM可観測性）
| 項目 | 値 |
|-----|----|
| **役割** | LLMトレーシング・コスト監視・プロンプト管理 |
| **外部ポート** | 3001 |
| **内部ポート** | 3000 |
| **Version** | 3.37.0（固定） |
| **SDK公開鍵** | `pk-lf-clawstack-2026` |
| **SDK秘密鍵** | `sk-lf-clawstack-2026` |
| **接続状態** | LiteLLM経由で全LLM呼び出しを自動トレース（2026-03-09 接続済み） |

**依存コンポーネント**:
- PostgreSQL（メタデータDB、`langfuse` DB）
- ClickHouse（時系列イベントDB）
- MinIO（S3互換ストレージ、`langfuse-events` バケット）
- Redis（キャッシュ）

**重要な設定**:
```
NEXT_PUBLIC_LANGFUSE_RUN_NEXT_INIT=false  ← ZodError バグ回避（必須）
CLICKHOUSE_MIGRATION_URL=clickhouse://langfuse:langfuse@clickhouse:9000/langfuse  ← 認証情報必須
```

### 8-2. ClickHouse（列指向DB）
| 項目 | 値 |
|-----|----|
| **役割** | Langfuse のイベント時系列ストレージ |
| **外部ポート** | 8123 (HTTP), 9000 (Native TCP) |
| **Version** | 24.8 |
| **ストレージ** | `clickhouse_data`（named Docker volume ← Windowsでbind mountは動作不可） |

### 8-3. P017 Workflow Self-Healer
- n8n ワークフロー（ID: `vc0kATBeDoQxKgPY`）
- 15分毎に全n8nワークフローの状態確認
- 異常時: restart×2 → LLM修復（qwen2.5-coder:7b）×2 → Telegram escalate
- スクリプト: `/home/node/clawd/workflow_healer.py`
- docker CLIが `/usr/local/bin/docker` にマウントされ、n8nからgaterayへ exec 可能

---

## 9. ストレージ基盤

### 9-1. PostgreSQL
| 項目 | 値 |
|-----|----|
| **外部ポート** | 5432 |
| **Version** | 16 |
| **使用DB** | `postgres`（メイン）, `langfuse`（Langfuse）, `dify`（Dify） |

### 9-2. Redis
| 項目 | 値 |
|-----|----|
| **外部ポート** | 6379 |
| **Version** | 7 |
| **用途** | Paperless キュー, LiteLLM キャッシュ, Langfuse, Dify |

### 9-3. MinIO（S3互換オブジェクトストレージ）
| 項目 | 値 |
|-----|----|
| **外部ポート** | 9000 (API), 9001 (Console) |
| **バケット** | `langfuse-events`（Langfuse用） |
| **アクセス** | minioadmin / （.envより） |

---

## 10. Web検索

### 10-1. SearXNG（プライベートWeb検索）
| 項目 | 値 |
|-----|----|
| **役割** | メタサーチエンジン（Google/Bing/DuckDuckGoを集約） |
| **外部ポート** | 8086（root compose）/ 8081（clawstack_v2 compose） |
| **内部URL** | `http://searxng:8080` |
| **JSON API** | `GET /search?q=<query>&format=json` |
| **使用箇所** | Open WebUI の Web検索バックエンド + clawstack-tools MCPの `web_search` |

---

## 11. UIレイヤー

### 11-1. Open WebUI
| 項目 | 値 |
|-----|----|
| **役割** | Ollama連携チャットUI。RAG + Web検索統合 |
| **外部ポート** | 3002 |
| **LLM** | Ollama (http://ollama:11434) |
| **Web検索** | SearXNG (http://searxng:8080) |
| **VectorDB** | Qdrant (http://qdrant:6333) ← 2026-03-09 接続済み |
| **注意** | Qdrantの`universal_knowledge`コレクションとは別コレクションを使用（Open WebUI管理） |

### 11-2. Portal Server
| 項目 | 値 |
|-----|----|
| **役割** | Nginx静的ファイルサーバー。ポータルUI + 各種ツールHTML |
| **外部ポート** | 8088 |
| **マウント** | `data/workspace/` → `/usr/share/nginx/html/` |

**内蔵HTMLアプリ**:
- Tolerance Center: `/apps/tolerance_hub/index.html`
- Injection Molding Hub: `/apps/molding_hub/index.html`
- AI Video Factory: `/apps/video_factory/index.html`
- Note Pro Writer: `/apps/note_pro/index.html`
- Kindle Author: `/apps/kindle_author/index.html`
- Kinematics Hub: `/apps/kinematics_hub/index.html`
- OpenRadioss Hub: `/apps/radioss_hub/index.html`

### 11-3. Dify AI Workflow Platform
| 項目 | 値 |
|-----|----|
| **役割** | ノーコードAIワークフロー・エージェントビルダー |
| **外部ポート** | 8092 (Web), 5001 (API) |
| **構成** | dify-api + dify-worker + dify-web + dify-plugin-daemon |
| **LLM** | Ollama連携 |
| **DB** | 専用PostgreSQL (port 5433) + 専用Redis (port 6381) |

---

## 12. 品質・エンジニアリングアプリ

### 12-1. WorkStudy AI（作業研究）
| 項目 | 値 |
|-----|----|
| **役割** | 動画から作業者の骨格推定 → Therbligs + MOST動作分析 → PDF/Excelレポート |
| **外部ポート** | 7870 |
| **技術** | MediaPipe, Gradio UI, MOST計算エンジン |
| **LLM連携** | Ollama（レポートコメント自動生成） |
| **メモリ制限** | 6GB |

### 12-2. Quality QA Dashboard
| 項目 | 値 |
|-----|----|
| **役割** | FMEA・統計分布・QIF品質データ可視化（Streamlit） |
| **外部ポート** | 8090 |

### 12-3. IATF System (Rails)
| 項目 | 値 |
|-----|----|
| **役割** | IATF 16949コンプライアンス管理・品質文書管理 |
| **外部ポート** | 3000 |

### 12-4. DXF → 3D Converter
| 項目 | 値 |
|-----|----|
| **役割** | 複雑な組立DXF（金型・板金）をレイヤー別3D STEPに変換 |
| **外部ポート** | 8003 (root) / 8002 (v2) |
| **技術** | FreeCADCmdバックエンド, manifold3d (CSG), Qwen3:8b 自己チェック |
| **AI自己検査** | `qwen3:8b`（think: False必須）でDXF変換品質を自動評価 |

---

## 13. CAE・シミュレーション

### 13-1. OpenRadioss（クラッシュ解析）
- 外部アクセス: docker exec 経由
- OpenRadioss 20260120（Dockerfile管理）
- データ: `/work` 共有ボリューム

### 13-2. OpenFOAM（CFD流体解析）
- 外部アクセス: docker exec 経由
- `opencfd/openfoam-dev:latest`

### 13-3. Project Chrono（マルチボディシミュレーション）
- 外部アクセス: docker exec 経由
- `uwsbel/projectchrono:latest`

### 13-4. Antigravity（エンジニアリング統合コンテナ）
| 項目 | 値 |
|-----|----|
| **役割** | FreeCAD・OpenFOAM・Blender・ElmerFEM・CalculiX・OpenRadioss・Godot等を統合 |
| **Dockerfileビルド** | `clawstack_v2/docker/antigravity/Dockerfile`（約60レイヤー・超細粒度分割） |
| **ビルドキャッシュ** | `clawstack_v2/data/buildcache/antigravity/` (local type, mode=max) |

**搭載アプリ（全Dockerfile管理・バージョン固定・再現性保証）**:
- FreeCAD 0.21.2, OpenFOAM, Blender, CalculiX, Netgen, ElmerFEM
- OpenRadioss 20260120, Godot 4.2.1, Rhubarb 1.13.0
- Impact FEM, rclone, Remotion
- Python/R 科学計算スタック

> **P017 最重要制約**: `--no-cache` ビルド完全禁止。ビルド時間30〜60分。

---

## 14. 生成・創作ツール

### 14-1. VoiceVox（日本語音声合成）
- **外部ポート**: 50021
- **API**: `POST /audio_query`, `POST /synthesis`
- CPU版（4スレッド）

### 14-2. Stable Diffusion（AI画像生成、profile=content / 無効化中）
- 外部ポート: 7861
- 現在 root compose では無効化（registry issue）

### 14-3. MiniGame Factory
| 項目 | 値 |
|-----|----|
| **役割** | SpecJSONからHTML5ゲーム・Android APK自動生成 |
| **UI外部ポート** | 3100 |
| **API外部ポート** | 8100 |
| **DB** | 専用PostgreSQL (port 5442) + 専用Redis (port 6389) |

---

## 15. 検索・インデックス

### 15-1. Meilisearch（全文検索、profile=content）
- **外部ポート**: 7700
- **マスターキー**: `clawstack_search_master_2026`
- 全文検索用インデックスエンジン（Qdrantとは別、キーワード検索特化）

---

## 16. ビジョン・アノテーション（profile=vision）

| サービス | ポート | 役割 |
|---------|-------|------|
| CVAT | 8082 | 画像・動画ラベリング |
| Label Studio | 8083 | アノテーションプラットフォーム |
| FiftyOne | 5151 | データセット可視化 |
| Vision Worker | 7860 | カスタム画像解析（Gradio/Streamlit） |

---

## 17. AIエージェント制御（GCTMSハーネス）

### SOUL.md — 17の運用ルール（抜粋）
| Rule | 内容 |
|------|------|
| Prime Directives | PROMISES.md最優先・事実の尊重・報告義務・セキュリティ遵守 |
| Rule 4 | LLM使い分け（Gemini Flash優先 → Groq → ローカル） |
| Rule 9 | ツール実行後に必ず日本語で結果報告 |
| Rule 10 | Model Not Found時の自己修復プロトコル |
| Rule 11 | OpenRadioss チェックポイント義務化 |
| Rule 14 | Brain & Brawnモデル（高コストLLMでコード生成のみ、実行はローカル） |
| Rule 16 | **Context Tracking**: 複数ステップ作業中は `[進捗X/Y]` で状態報告 |
| Rule 17 | **Supervision**: 完了・失敗時に `✅/❌ [理由分類]` 形式で構造化報告 |

### PROMISES.md — 主要な約束事項
| ID | 内容 |
|----|------|
| P017 | Dockerビルドキャッシュ必須使用（最重要） |
| P018 | Antigravity Dockerfile超細粒度分割（1パッケージ1RUN） |
| P021 | Human-in-the-Loop承認フロー（自動/要承認/禁止の3段階） |

### P021 承認フロー
| レベル | 対象操作 |
|-------|---------|
| **自動実行** | ログ閲覧・情報検索・ステータス確認・読み取り専用操作 |
| **要承認（Telegram）** | 設定ファイル変更・外部書き込み・n8nワークフロー変更 |
| **禁止** | 本番DB削除・認証情報外部送信・`--no-cache`ビルド |

---

## 18. ポートマップ（全サービス）

| ポート | サービス | 役割 |
|--------|---------|------|
| 1880 | Node-RED | IoT/MQTTフロー制御 |
| 1883 | Mosquitto | MQTTブローカー |
| 3000 | IATF System | IATF品質管理（Rails） |
| 3001 | Langfuse | LLM可観測性 |
| 3002 | Open WebUI | LLMチャットUI |
| 3100 | MiniGame UI | ゲーム生成フロントエンド |
| 4000 | LiteLLM | LLMゲートウェイ |
| 5001 | Dify API | AIワークフローAPI |
| 5055 | Open Notebook API | NotebookLM API |
| 5151 | FiftyOne | データセット可視化 |
| 5432 | PostgreSQL | メインRDB |
| 5442 | PostgreSQL (MiniGame) | MiniGame専用DB |
| 5679 | n8n | ワークフロー自動化 |
| 6333 | Qdrant | ベクトルDB |
| 6379 | Redis | キャッシュ/キュー |
| 6389 | Redis (MiniGame) | MiniGame専用キャッシュ |
| 7700 | Meilisearch | 全文検索 |
| 7860 | Vision Worker | 画像解析Gradio |
| 7861 | Stable Diffusion | AI画像生成 |
| 7870 | WorkStudy AI | 動作分析Gradio |
| 7997 | Infinity | 埋め込みサーバー |
| 8000 | Paperless NGX | 文書管理 |
| 8001 | SurrealDB | Open Notebook DB |
| 8003 | DXF3D App | DXF→3D変換 |
| 8082 | CVAT | 画像ラベリング |
| 8083 | Label Studio | アノテーション |
| 8085 | Stirling PDF | PDF処理 |
| 8086 | SearXNG | Web検索（root compose） / llama.cpp（v2 compose） |
| 8087 | Docling | 文書パーサー |
| 8088 | Portal (Nginx) | ポータルUI |
| 8090 | Quality Dashboard | 品質ダッシュボード |
| 8092 | Dify Web | Dify UI |
| 8100 | MiniGame API | ゲーム生成API |
| 8123 | ClickHouse | Langfuse時系列DB |
| 9000 | MinIO API | オブジェクトストレージ |
| 9001 | MinIO Console | MinIO管理UI |
| 9876 | clawstack-tools MCP | RAG+Web検索MCPサーバー |
| 11434 | Ollama | ローカルLLM |
| 18789 | OpenClaw Gateway | メインAIエージェント |
| 18791 | OpenClaw Browser | CDPブラウザ制御 |
| 50021 | VoiceVox | 日本語音声合成 |

---

## 19. データフロー（全体）

```
ユーザー
  ↓ Telegram / OpenClaw Chat UI (port 18789)
OpenClaw Gateway (clawdbot-gateway)
  ├─ LiteLLM (port 4000)
  │    ├─ Google Gemini 2.5 Flash (cloud) [Primary]
  │    ├─ Groq llama-3.3-70b (cloud) [Fast/Tools]
  │    ├─ Ollama deepseek-r1:14b (local) [Offline]
  │    └─ Infinity mxbai-embed-large-v1 (local) [Embedding]
  │         └─ → Langfuse (全呼び出しトレース)
  ├─ MCP: clawstack-tools (port 9876)
  │    ├─ rag_search → Infinity embed → Qdrant
  │    └─ web_search → SearXNG
  ├─ MCP: n8n-workflows (port 5678)
  │    ├─ ワークフロー検索・実行
  │    └─ → Docker exec → gateway scripts
  ├─ Browser (Playwright Chromium)
  │    → 各種Web UI操作
  └─ exec (docker exec / subprocess)
       ├─ CalculiX, OpenRadioss, ElmerFEM (CAE)
       ├─ python3 scripts/
       └─ その他CLIツール

文書取り込みパイプライン:
  Paperless NGX
    ↓ ingest_watchdog.py
    ↓ minicpm-v VLM (画像ページ)
    ↓ Infinity embed
    → Qdrant universal_knowledge

  CETOL6σ/FEM PDF (スキャン)
    ↓ ingest_cetol_fem_docling.py
    ↓ Tesseract OCR + minicpm-v VLM (ハイブリッド)
    ↓ Infinity embed
    → Qdrant universal_knowledge

n8n 自動監視:
  Ingest Watchdog Supervisor (5分毎)
    → watchdog.py 死活確認・再起動・Telegram通知
  P017 Self-Healer (15分毎)
    → 全ワークフロー健全性確認・LLM自己修復
```

---

## 20. セキュリティ・制約事項

### ネットワーク分離
- 全サービス: `127.0.0.1` バインド（LAN外部アクセス不可）
- Docker内部通信のみ有効

### 禁止事項（Prime Directives）
1. 本番DB接続設定ファイルの変更禁止
2. 外部ネットワークへの認証情報送信禁止
3. `rm -rf`等の破壊的コマンド自律実行禁止
4. `--no-cache`ビルド禁止（P017）
5. 秘密鍵・APIキーの出力マスク

### エラー発生時の自己修復
- 3回自律修正試行（P015）
- n8n P017 Self-Healer による自動監視・Telegram通知
- 修復不能時はエスカレート（鈴木さんへ通知）

---

## 21. 現在の課題・制限

| 課題 | 詳細 | 状態 |
|------|------|------|
| CETOL/FEM RAG品質 | スキャンPDF→VLM説明で取り込んだため品質が低かった | 修正中（ハイブリッドOCR+VLMで再インジェスト実行中） |
| clawstack-tools MCP | ゲートウェイが3/7起動で新MCP未認識 | インジェスト完了後にgateway restart予定 |
| Native/Docker Ollama競合 | Windows Native OllamaとDocker Ollamaがport競合リスク | 運用で管理（内部URLで回避） |
| Groq TPM制限 | 無料枠6,000 TPM/min = OpenClawシステムプロンプト（7,237トークン）で超過 | OpenClawのprimaryモデルとしては使用不可、補助のみ |

---

*このドキュメントは自動生成されました。最終更新: 2026-03-09*
*生成スクリプト: Claude Code (claude-sonnet-4-6) in d:\Clawdbot_Docker_20260125*
