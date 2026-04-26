# Clawstack AI Engineering Platform — システムプロトコル v2.1
**作成日**: 2026-03-10
**前バージョン**: v2.0 (2026-03-10)
**対象**: ChatGPT / Antigravity / 外部LLMによるシステム評価・改善提案用
**ホスト**: Windows 11 Pro, Docker Desktop (WSL2), MiniPC (Intel N100 / RAM 32GB / NVMe 2TB)
**Compose プロジェクト名**: `clawstack-unified`

---

## 0. この文書の位置づけ

本書は、Clawstack / OpenClaw 環境の構成・制約・既知課題・改善方針を、外部LLMやAIエージェントに正確に伝えるための**共有版プロトコル**である。

### 共有版ポリシー
- 本文には**実運用の秘密情報を記載しない**
- 認証情報、APIキー、Bearer token、メールアドレス、パスワード、JWT、秘密鍵はすべて `.env` または Secret 管理に保持する
- 本文中のプレースホルダは実値に置換しないこと
- 破壊的変更、秘密の外部送信、本番DB削除、自律的な危険操作は禁止

### この文書の目的
1. 現状アーキテクチャを外部LLMへ誤解なく伝える
2. 監視の見える化だけでなく、**改善につながる提案**を得る
3. OpenClaw の AIハーネス / GCTMS / Human-in-the-Loop が有効に働いているか評価する
4. Langfuse を中心とした可観測性基盤を強化する
5. Portal 上で見やすく、日常的に確認したくなる監視UIを設計する

---

## 1. システム概要

Clawstack は、機械設計・品質・製造業務の自動化を目的として構築した、**完全ローカル稼働・プライバシー優先の AI エンジニアリングプラットフォーム**である。
OpenClaw を中心とし、LLM、RAG、MCP、n8n、文書管理、可観測性、専門アプリ群を Docker ネットワーク内で統合運用している。

### 設計哲学
- **無料OSS優先**: 有料クラウドAPIは補助・フォールバック用途に限定
- **ローカルファースト**: 可能な限りローカル完結
- **Dockerコンテナ完結**: 40+ コンテナが内部ネットワークで連携
- **AIエージェント中心**: OpenClaw が複数サービスを横断制御
- **RAG活用**: 社内技術文書・PDF・OCR文書を自動インジェストして検索
- **AIハーネス制御**: GCTMS（Guard / Context / Tool / Memory / Supervision）
- **LLMOps可観測性**: Langfuse v3 を主軸にトレース・スコア・運用監視を行う
- **改善重視**: 可視化は目的ではなく、改善候補抽出と運用判断につなげる

### ハードウェア
```
CPU: Intel N100 (4コア)
RAM: 32GB
Storage: NVMe 2TB
GPU: なし（CPU推論のみ）
OS: Windows 11 Pro
Docker: Desktop (WSL2 backend)
```

---

## 2. ネットワーク構成

### 2-1. 外部公開ポート（Host: 127.0.0.1）

```
:18789  OpenClaw Gateway
:18791  OpenClaw Browser CDP
:5679   n8n
:1880   Node-RED
:8088   Portal (nginx)
:8081   SearXNG
:8000   Paperless-ngx
:6333   Qdrant
:3001   Langfuse UI
:7870   WorkStudy AI
:8090   Quality Dashboard
:8087   Docling
:7997   Infinity (embedding)
:9000   MinIO API
:9001   MinIO Console
:5432   PostgreSQL
:6379   Redis
:11434  Ollama (Host 参照時)
:50021  VoiceVox
:3100   MiniGame UI
:8100   MiniGame API
```

### 2-2. Docker内部通信（Network: clawstack-unified）

```
openclaw        -> litellm:4000
openclaw        -> qdrant:6333
openclaw        -> n8n:5678 (MCP経由)
openclaw        -> clawstack-mcp:9876
clawstack-mcp   -> infinity:7997
clawstack-mcp   -> qdrant:6333
clawstack-mcp   -> searxng:8080
litellm         -> langfuse:3000
langfuse-worker -> redis:6379
langfuse-worker -> clickhouse:8123
langfuse        -> postgres:5432
langfuse        -> minio:9000
ingest_watchdog -> paperless
ingest_watchdog -> infinity
ingest_watchdog -> qdrant
portal          -> langfuse / service health APIs
```

### 2-3. 表記ルール

Host URL と Docker service 名 を区別する

```
例:
  Langfuse UI:      http://localhost:3001
  Langfuse service: http://langfuse:3000
```

外部LLMに提案を求める際は、Host port と internal service port を混同しないこと

---

## 3. AIエージェント層（コア）

### 3-1. OpenClaw Gateway

| 項目 | 値 |
|-----|----|
| 役割 | メインAIエージェント。全サービスの自律制御・会話UI |
| Host Port | 18789 |
| Browser CDP Host Port | 18791 |
| 認証 | `.env` の `<OPENCLAW_BEARER_TOKEN>` |
| Browser | Playwright Chromium (headless) |
| 主要連携先 | LiteLLM / Qdrant / MCP / n8n / Browser / exec |
| MCP servers | `n8n-workflows`, `clawstack-tools` |

#### モデル表記の統一

| 種別 | 表示名 | 実際のモデルID / 経路 |
|------|--------|----------------------|
| Primary LLM | Gemini 2.5 Flash | LiteLLM経由の `openai/gemini-2.5-flash` |
| Fallback LLM | Qwen 2.5 Coder 7B | LiteLLM経由の `openai/qwen2.5-coder:7b` → `http://ollama:11434/v1` |
| Embedding (主) | mxbai-embed-large-v1 | Infinity 経由 |
| Embedding (補助) | nomic-embed-text | Ollama 経由 |

#### コンテナ内主要ファイル（例: /home/node/clawd/）

| ファイル | 役割 |
|---------|------|
| `PORTAL_APPS.md` | 全アプリの使用方法・コンテキスト |
| `SOUL.md` | 自律行動規範 |
| `PROMISES.md` | 約束事項・禁止事項・承認フロー |
| `TOOLS.md` | ツール仕様 |
| `clawstack_tracing.py` | Langfuse v3 トレーシング補助 |
| `clawstack_mcp_server.py` | MCP サーバー本体 |
| `ingest_watchdog.py` | Paperless → RAG 自動インジェスト |
| `rag_search.py` | RAG検索CLI |
| `workflow_healer.py` | n8nワークフロー自己修復 |

### 3-2. LiteLLM Proxy

| 項目 | 値 |
|-----|----|
| 役割 | 複数LLMの統合管理、ルーティング、コスト計測 |
| Service | `litellm:4000` |
| Primary | `openai/gemini-2.5-flash` |
| Fallback | `openai/qwen2.5-coder:7b` via Ollama |
| Callback | `success_callback: ["langfuse"]` |
| 主用途 | LLM呼び出しの統一・トレース・失敗時フォールバック |

### 3-3. Clawstack MCP Server

| 項目 | 値 |
|-----|----|
| 役割 | OpenClaw から呼べる MCP ツール提供サーバー |
| Service | `clawstack-mcp:9876` |
| 起動 | `python3 /home/node/clawd/clawstack_mcp_server.py` |
| Transport | FastMCP streamable-http |
| 主ツール1 | `rag_search(query, collection, top_k)` |
| 主ツール2 | `web_search(query, num_results, engines)` |
| Tracing | Langfuse span で tool 呼び出し記録 |

#### MCP利用例
```
mcp__clawstack-tools__rag_search(query="CETOL 6sigma tolerance stackup", collection="universal_knowledge", top_k=5)
mcp__clawstack-tools__web_search(query="IATF 16949 revision 2024", num_results=5)
```

---

## 4. LLMOps 可観測性層

### 4-1. 基本方針

- Langfuse を運用監視の主軸とする
- LangSmith は必須ではない
- LangSmith を使う場合は、匿名化データまたは合成ベンチマーク限定の比較評価用途に留める
- 可視化は目的ではなく、失敗原因特定・改善候補抽出・運用判断につなげる

### 4-2. アーキテクチャ概要

```
OpenClaw request
    │
    ├─► LiteLLM ───────────────► Langfuse trace (LLM call)
    │
    ├─► MCP rag_search ────────► Langfuse span
    │
    ├─► MCP web_search ────────► Langfuse span
    │
    ├─► n8n workflow ──────────► metadata / status / trace linkage
    │
    ├─► Browser / exec ────────► span / event / status
    │
    └─► final response ────────► parent trace closed
```

### 4-3. 追跡の単位

1ユーザー依頼 = 1親trace とし、以下を子spanとして記録する。

```
harness_precheck
model_routing
rag_search
web_search
mcp_call
n8n_execute
browser_action
exec_command
self_healer
approval_wait
final_response
```

### 4-4. request_id / trace_id 伝播

以下の識別子を全体で引き回すこと。

| キー | 用途 |
|------|------|
| `request_id` | 1リクエスト単位の一意識別 |
| `trace_id` | 可観測性・横断追跡用 |
| `session_id` | 会話セッション単位 |
| `workflow_id` | n8n実行識別 |
| `document_id` | Paperless / RAG対象文書識別 |

伝播先: OpenClaw / LiteLLM metadata / MCP tools / n8n workflow input / Browser wrapper / exec wrapper / ingest_watchdog / workflow_healer / Portal のトレース詳細導線

### 4-5. Langfuse セットアップ

| 項目 | 値 |
|-----|----|
| Server | `langfuse/langfuse:3.x` |
| Worker | `langfuse/langfuse-worker:3.x` |
| DB | PostgreSQL |
| Queue | Redis |
| OLAP | ClickHouse |
| Events Storage | MinIO |
| UI (Host) | `http://localhost:3001` |
| Service URL | `http://langfuse:3000` |
| Project | `clawstack-prod` |
| 認証情報 | `.env` の `<LANGFUSE_PUBLIC_KEY>`, `<LANGFUSE_SECRET_KEY>` |

### 4-6. 記録する主要メトリクス

| メトリクス | 計測元 | 記録先 |
|-----------|--------|--------|
| LLM応答レイテンシ | LiteLLM callback | Langfuse trace |
| LLMコスト | LiteLLM callback | Langfuse trace |
| モデル選択 / fallback | routing metadata | Langfuse metadata |
| RAG関連性スコア | clawstack_tracing.py | Langfuse score `rag_relevance` |
| MCP tool 実行時間 | custom span | Langfuse span |
| Web検索レイテンシ | custom span | Langfuse span |
| self-heal 成功 / 失敗 | workflow_healer | Langfuse score / metadata |
| 要承認 / 禁止判定 | harness_precheck | Langfuse metadata |

### 4-7. 改善ループ

```
Trace収集
  ↓
KPI集計
  ↓
閾値逸脱 / 失敗trace 抽出
  ↓
改善候補自動要約
  ↓
人が承認
  ↓
Prompt / Routing / Tool / Workflow を修正
  ↓
再評価
```

### 4-8. 主要KPI / SLO（初期案）

| 項目 | 初期目標 |
|------|---------|
| OpenClaw 成功率 | 95%以上 |
| P95 レイテンシ | 20秒以内 |
| fallback率 | 15%以下 |
| MCP tool 成功率 | 97%以上 |
| self-heal 成功率 | 60%以上 |
| 要承認率 | 10%以下を目安 |
| RAG top score | 0.75以上を目安 |
| low_recall 発生率 | 継続的に低下させる |

### 4-9. Portal 可観測性Hub

- **URL**: `http://localhost:8088/apps/observability_hub/`
- **目的**: 監視だけでなく、改善候補と運用状況を一目で把握する
- **自動更新**: 30秒ごと

主な表示要素:
- OpenClaw Health Score
- AI Harness Effectiveness
- RAG Quality Monitor
- MCP / n8n Reliability
- Recent Recoveries
- Improvement Opportunities
- Latest Traces
- Cost / Latency Trend

UI方針:
- 状態バッジ: `Excellent` / `Stable` / `Watch` / `Recovery Needed`
- 今日のハイライト表示
- 良い改善を短文で可視化
- 業務監視として過度にゲーム化しない

### 4-10. LangSmith の位置づけ（任意）

- デフォルトでは無効
- 使う場合は匿名化または合成データ限定
- 実文書・実機密データの外部送信は禁止
- 役割は比較実験 / ベンチマーク / Prompt差分評価

---

## 5. RAG / ナレッジ管理層

### 5-1. Qdrant ベクトルDB

| コレクション | 次元数 | Embedモデル | 内容 |
|------------|--------|------------|------|
| `universal_knowledge` | 1024 | mxbai-embed-large-v1 | FMEA / 5Why / CETOL / FEM / Paperless 全文書 |
| `iatf_knowledge` | 768 | nomic-embed-text | IATF 16949 関連文書 |

### 5-2. Infinity Embedding Server

- Service: `infinity:7997`
- 主モデル: `mxbai-embed-large-v1`
- 用途: インジェスト・検索クエリベクトル化

### 5-3. Paperless-ngx + Ingest Watchdog

```
Paperless (OCR済み文書)
   ↓
ingest_watchdog.py (定期ポーリング)
   ├─ OCR text >= threshold: PyMuPDF 抽出
   ├─ OCR text < threshold:  VLM補助抽出
   ↓
Infinity embed
   ↓
Qdrant 登録
```

### 5-4. RAGクエリ品質ガイド

| ドキュメント種別 | 推奨クエリ言語 | 備考 |
|---------------|--------------|------|
| CETOL / FEM | 英語推奨 | VLM/画像由来の英語説明が多い |
| FMEA / 5Why | 日本語・英語可 | 比較的安定 |
| IATF 16949 | 英語推奨 | 専用 knowledge を参照 |

### 5-5. RAG品質改善の重点課題

- 日本語質問を英語へ自動補正する前処理の導入
- 低スコア時の言い換え / 再検索戦略
- Docling を使った PDF/DOCX/PPTX の構造化抽出強化
- Paperless OCR と VLM補助抽出の役割分担最適化
- ベンチセットに基づく継続評価

---

## 6. ワークフロー自動化層

### 6-1. n8n

| 項目 | 値 |
|-----|----|
| Host Port | 5679 |
| MCP endpoint | `http://n8n:5678/mcp-server/http` |
| MCP tools | `search_workflows`, `execute_workflow`, `get_workflow_details` |

#### 主要ワークフロー

| ID（プレースホルダ） | 名前 | 役割 |
|---------------------|------|------|
| `<WORKFLOW_ID_INGEST_WATCHDOG>` | Ingest Watchdog Supervisor | Watchdog 監視 |
| `<WORKFLOW_ID_SELF_HEALER>` | P017 Workflow Self-Healer | n8nワークフロー障害の検知・修復 |

### 6-2. Self-Healer 修復戦略

```
エラー検出
  ↓
restart × 2
  ↓
限定ファイルへの LLM 修正 × 2
  ↓
ヘルスチェック
  ↓
失敗時は Telegram / UI へエスカレーション
```

### 6-3. Self-Healer 安全ガード

- 修正前バックアップを必須化
- 許可リスト方式で修正対象ファイルを限定
- `.env`, compose, DB設定, 認証情報, secrets は自動修正禁止
- 修正差分を記録
- dry-run モードを持つ
- 要承認操作は P021 に従う
- 修正後にヘルスチェック必須
- ロールバック手順を保持する

### 6-4. Node-RED

- IoT / データフロー用途
- 現時点ではスタンバイ寄り
- 重複機能が増える場合は整理候補

---

## 7. ローカルLLM層

### 7-1. Docker Ollama

| モデル | 用途 |
|--------|------|
| `qwen2.5-coder:7b` | LiteLLM fallback / コード補助 |
| `deepseek-r1:7b` | 推論補助 |
| `deepseek-r1:14b` | 高精度推論 |
| `minicpm-v` | VLM / 画像解釈 |
| `nomic-embed-text` | 補助 embedding |
| `llava` | 補助 VLM |

### 7-2. 重要注意

- Native Windows Ollama と Docker Ollama の2系統が存在する可能性がある
- 原則として OpenClaw / LiteLLM / 内部サービスは Docker Ollama を使用する
- 監視では `ollama_target=docker/native/unknown` を記録できると望ましい
- `localhost` / `host.docker.internal` の誤用は既知の事故要因

### 7-3. Gemini API

- 利用時は LiteLLM 経由
- 実鍵は `.env` 管理
- 無料枠 / 制限 / 一時障害時はローカルモデルへフォールバック

---

## 8. 文書管理・解析層

### 8-1. Paperless-ngx
- OCR付き文書管理
- 文書取り込み後に RAG へ自動インジェスト

### 8-2. Docling
- PDF / DOCX / PPTX を Markdown / 構造化テキストへ変換
- RAG前処理改善の重要コンポーネント

### 8-3. Dify
- LLMアプリ構築プラットフォーム
- 現状はスタンバイ寄り
- OpenClaw / n8n / Portal と重複する用途があるため整理対象候補

---

## 9. 専門アプリ層

### 9-1. WorkStudy AI
- 動画から作業動作を解析し、MOST分析を行う

### 9-2. Quality Dashboard
- Streamlit製
- 品質データの可視化

### 9-3. DXF → 3D アプリ
- DXF から CSG / 3D形状を生成
- 自己チェックロジックあり

### 9-4. Portal Apps

| アプリ | URL |
|--------|-----|
| Observability Hub | `/apps/observability_hub/` |
| Tolerance Center | `/apps/tolerance_hub/` |
| Injection Molding Hub | `/apps/molding_hub/` |
| Kinematics Hub | `/apps/kinematics_hub/` |
| OpenRadioss Hub | `/apps/radioss_hub/` |

---

## 10. インフラ層

### 10-1. PostgreSQL
- n8n / Langfuse / Paperless / その他サービスの永続DB

### 10-2. Redis
- ジョブキュー / キャッシュ
- 認証設定の扱いは改善余地あり

### 10-3. MinIO
- S3互換オブジェクトストレージ
- Langfuse event storage 等に使用

### 10-4. ClickHouse
- Langfuse v3 の OLAP / 集計基盤

### 10-5. SearXNG
- プライベート Web メタ検索
- MCP web_search のバックエンド

### 10-6. VoiceVox
- ローカル日本語TTS

### 10-7. 保持期間 / バックアップ / TTL（改善推奨）

最低限、以下を設計対象とする。

- Langfuse trace 保持期間
- ClickHouse TTL
- MinIO lifecycle
- PostgreSQL backup 頻度
- Qdrant snapshot 頻度
- `ingest_watchdog_state.json` のバックアップ
- 大容量ログのローテーション

---

## 11. AIハーネス制御フレームワーク (GCTMS)

```
G - Guard       : 承認フロー / 禁止操作 / 安全判定
C - Context     : PORTAL_APPS.md / TOOLS.md / 業務文脈
T - Tool        : MCP / n8n / RAG / Browser / exec
M - Memory      : Qdrant / 会話メモリ / embedding
S - Supervision : SOUL / PROMISES / Self-Healer / 構造化報告
```

### 11-1. Human-in-the-Loop 承認フロー (P021)

| レベル | 対象操作 |
|--------|---------|
| 自動実行 | 読み取り専用、ログ参照、検索、状態確認 |
| 要承認 | 依存更新、compose変更、外部書き込み、workflow変更 |
| 禁止 | 本番DB削除、秘密の外部送信、`--no-cache` ビルド |

### 11-2. 可観測性で検証したいこと

- GCTMS が実際に事故防止に役立っているか
- 承認が必要な操作を正しく止めているか
- 自動実行と要承認の境界が適切か
- self-heal が安全に機能しているか
- ルーティング / RAG / MCP が実務上有効か

---

## 12. データフロー全体図

```
[User / Telegram / UI]
        │
        ▼
[OpenClaw Gateway]
        │
   ┌────┼──────────────────────────────────────┐
   │    │                                      │
   │    ▼                                      ▼
   │ [LiteLLM Proxy]                     [MCP: clawstack-tools]
   │    │                                      │
   │    ├──► [Langfuse]                        ├──► [RAG search]
   │    │                                      │        │
   │    ▼                                      │        ▼
   │ [Gemini / Ollama]                         │    [Infinity]
   │                                           │        │
   │                                           │        ▼
   │                                           │    [Qdrant]
   │                                           │
   │                                           └──► [Web search]
   │                                                     │
   │                                                     ▼
   │                                                 [SearXNG]
   │
   ├──► [n8n workflows]
   │
   ├──► [Browser / exec]
   │
   └──► [final response]

[Paperless] ─► [ingest_watchdog] ─► [Docling / OCR / VLM補助] ─► [Infinity] ─► [Qdrant]
```

---

## 13. セキュリティ / 共有ルール

- 全サービスは原則 `127.0.0.1` バインド
- APIキー、トークン、パスワードは `.env` または Secret 管理
- Git 管理対象に秘密情報を含めない
- 共有版文書には実値を載せない
- 外部LLMに機密文書本文をそのまま送らない
- LangSmith 等のクラウド評価は匿名化 / 合成データ前提
- 本番変更は承認フローを通す

---

## 14. 既知の課題・制限事項

| 課題 | 影響 | 対応状況 / 備考 |
|------|------|---------------|
| Redis auth 警告 | 一部サービスが認証付き接続を試みる | 軽微だが整理余地あり |
| CETOL / FEM RAGスコア低 | 日本語クエリで recall が落ちる | 英語クエリ補正が有効な可能性 |
| MCP 認識ズレ | clawstack-tools 未認識や再読込不足が起こる可能性 | registry refresh / restart 観測が必要 |
| Native / Docker Ollama 競合 | 誤接続・遅延・失敗の原因 | trace で接続先識別したい |
| GPU なし | 大型モデル推論が遅い | CPU前提で割り切り |
| Langfuse SDK 互換差分 | 一部ヘルスチェック補助で相性問題 | trace送信そのものは可能 |
| Groq 等の外部制限 | 将来的に TPM / rate limit の影響あり得る | 外部モデル利用時のみ監視対象化 |
| Dify / Node-RED 重複 | 機能が散らばる可能性 | 役割整理候補 |

---

## 15. v2.0 → v2.1 変更サマリー

| 変更内容 | 詳細 |
|---------|------|
| 秘密情報の除去 | 実トークン・鍵・パスワードをプレースホルダ化 |
| ポート表記の整理 | Host Port / Internal Service の記述を統一 |
| モデル名の統一 | 表示名 / 実モデルID / 経路を分離 |
| 改善ループ追記 | 可視化から改善へつなぐ運用ループを明記 |
| KPI / SLO 追加 | 成功率・遅延・fallback率などの初期目標を追加 |
| trace_id 伝播追記 | request_id / trace_id / session_id の引き回しを明文化 |
| Self-Healer 安全策強化 | バックアップ・差分・許可リスト・ロールバックを追記 |
| 既知課題を拡張 | MCP認識・Ollama競合・将来の外部制限も記載 |
| Portal UX方針追加 | 見やすさ + 改善につながるUIの方向性を明確化 |

---

## 16. 評価依頼ポイント（外部LLM / Antigravity 向け）

以下の観点で、破壊的変更を避けつつ、最小差分で改善提案してほしい。

1. **MCP活用度の最適化**
   clawstack-tools MCP（RAG / Web検索）と n8n MCP の使い分けは適切か。冗長性や不足はないか。

2. **トレーシング設計の妥当性**
   LiteLLM callback + custom span + request_id 伝播の構成は適切か。OpenClaw 1依頼全体を親trace化する設計はどうあるべきか。

3. **RAG品質向上策**
   VLM由来・OCR由来の文書に対して、検索精度を根本改善する方法は何か。英訳前処理、構造化抽出、再検索戦略、評価ベンチ設計を提案してほしい。

4. **アーキテクチャ整理**
   Dify / Node-RED / 一部ワークフロー等、重複または休眠気味のコンポーネントをどう整理すべきか。

5. **CPU限定環境での最適化**
   Intel N100 / 32GB / GPUなし の前提で、最も効率のよいモデル・役割分担は何か。

6. **Self-Healer の信頼性**
   restart → 限定修正 → ヘルスチェック → エスカレーション の流れは堅牢か。さらに必要な安全装置は何か。

7. **Portal 可観測性Hub の改善**
   見栄えだけでなく、改善につながるUI/UXにするには何を追加すべきか。ただし、業務監視として過度にゲーム化しないこと。

8. **Langfuse / LangSmith の役割分担**
   運用監視は Langfuse、比較評価は LangSmith という設計は妥当か。もっと適した構成があるか。

---

## 17. 実装・提案時の制約

提案や実装案を出す際は、以下を守ること。

- 既存の Langfuse 連携を壊さない
- 破壊的変更は禁止
- 本番DB削除は禁止
- 秘密情報を外部へ送らない
- `--no-cache` ビルドは禁止
- 変更前に影響範囲とロールバック手順を示す
- まずは最小変更で改善する
- Portal の可観測性Hubは、見やすく、改善に直結し、少し楽しいことを目指す

---

## 18. 外部LLMへの希望出力形式

回答は次の順で返してほしい。

1. 現状認識サマリー
2. 推奨アーキテクチャ
3. 最小変更プラン
4. 変更対象ファイル一覧
5. 実装コード案
6. docker-compose / env 差分案
7. Langfuse metadata / score 設計
8. Portal UI / カード案
9. テスト計画
10. ロールバック計画
11. 今回は実装しないが将来候補の一覧
