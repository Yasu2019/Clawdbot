# Clawstack V2 ポータル — エージェント操作ガイド

あなた（OpenClaw）はこのファイルに記載された全アプリを自律的に操作できます。
ブラウザ操作には `openclaw browser` コマンド群を使います。APIがある場合は直接HTTPリクエストが高速です。

## モデル切り替えポリシー（重要）

AIモデルは以下の優先順位でフォールバックします：

1. **google/gemini-2.0-flash**（通常使用・最高品質）
2. **google/gemini-2.0-flash-lite**（Gemini APIレート制限時・自動切り替え）
3. **ollama/deepseek-r1:14b**（Gemini全体が制限中・ローカルLLM）

**モデルが切り替わったことに気づいた場合（応答速度の変化、精度の変化など）は、返答の冒頭で必ず理由を一言添えてください。**
例：「（注：Gemini APIのレート制限に達したため、現在ローカルモデル deepseek-r1 で動作中です）」

---

## ブラウザ操作の基本

```bash
# ブラウザ起動
openclaw browser start

# URLを開く
openclaw browser navigate "$BROWSER_N8N_URL"

# スナップショット（AI用のDOM要約）を取得してから操作
openclaw browser snapshot

# スクリーンショット
openclaw browser screenshot

# クリック（snapshotで得たref番号を使う）
openclaw browser click <ref>

# テキスト入力
openclaw browser type <ref> "入力テキスト"
```

---

## アプリ一覧と操作方法

### 1. OpenClaw Chat (AI) — Port 18789

- **用途**: 会話・タスク指示・ステータス確認
- **ブラウザURL**: `http://host.docker.internal:18789`
- **操作**: 自分自身のUIなので通常は直接操作不要

---

### 2. n8n Automation — Port 5679

- **用途**: ワークフロー自動化・Webhook管理・外部API連携
- **ブラウザURL**: `$BROWSER_N8N_URL` (<http://host.docker.internal:5679>)
- **内部API**: `$N8N_API_URL` (<http://n8n:5678/api/v1>)
- **MCP Server**: `$N8N_MCP_URL` (<http://n8n:5678/mcp-server/http>) — **OpenClawのMCPに登録済み（n8n-workflows）**
- **API操作例**:

  ```bash
  # ワークフロー一覧
  curl -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_API_URL/workflows"
  # ワークフロー実行
  curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_API_URL/workflows/{id}/execute"
  ```

- **MCP経由の操作**: OpenClawエージェントは直接MCPツールを使ってn8nのワークフローを操作できる
  - `mcp__n8n-workflows__search_workflows` — ワークフロー検索
  - `mcp__n8n-workflows__execute_workflow` — ワークフロー実行
  - `mcp__n8n-workflows__get_workflow_details` — 詳細取得
- **ブラウザ操作**: ワークフロー作成・編集はブラウザUIから

---

### 3. Node-RED (IoT) — Port 1880

- **用途**: MQTT・センサーデータ処理・産業IoTフロー
- **ブラウザURL**: `$BROWSER_NODERED_URL` (<http://host.docker.internal:1880>)
- **内部API**: `$NODERED_URL` (<http://nodered:1880>)
- **API操作例**:

  ```bash
  # フロー一覧
  curl "$NODERED_URL/flows"
  # フロー更新
  curl -X PUT "$NODERED_URL/flow/{id}" -H "Content-Type: application/json" -d '{...}'
  # インジェクトノード起動
  curl -X POST "$NODERED_URL/inject/{nodeId}"
  ```

---

### 4. Quality QA Dashboard — Port 8090

- **用途**: FMEA・統計分布・QIF トラッキング（Streamlit）
- **ブラウザURL**: `$BROWSER_QUALITY_DASHBOARD_URL` (<http://host.docker.internal:8090>)
- **操作**: ブラウザ経由でStreamlitUIを操作。ファイルアップロード・パラメータ入力など

---

### 5. WorkStudy AI — Port 7870

- **用途**: Therbligs + MOST動作分析・骨格推定・PDF/Excel出力（Gradio）
- **ブラウザURL**: `$BROWSER_WORKSTUDY_URL` (<http://host.docker.internal:7870>)
- **操作**: Gradio UIをブラウザで操作。動画ファイルをアップロードして解析実行

---

### 6. Paperless NGX — Port 8000

- **用途**: 文書管理・OCR・PDF格納
- **ブラウザURL**: `$BROWSER_PAPERLESS_URL` (<http://host.docker.internal:8000>)
- **内部API**: `$PAPERLESS_API_URL` (<http://paperless:8000/api>)
- **認証**: Token認証（初回はBasic: admin/admin でトークン取得）
- **API操作例**:

  ```bash
  # トークン取得
  TOKEN=$(curl -s -X POST "$PAPERLESS_API_URL/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

  # 文書一覧
  curl -H "Authorization: Token $TOKEN" "$PAPERLESS_API_URL/documents/"

  # 文書アップロード
  curl -H "Authorization: Token $TOKEN" \
    -F "document=@/path/to/file.pdf" \
    "$PAPERLESS_API_URL/documents/post_document/"
  ```

---

### 7. Open Notebook App — Port 8502 / API 5055

- **用途**: ローカルNotebookLMクローン（Ollama連携）
- **ブラウザURL**: `$BROWSER_OPEN_NOTEBOOK_URL` (<http://host.docker.internal:8502>)
- **内部API**: `$OPEN_NOTEBOOK_API_URL` (http://open_notebook:5055)
- **操作**: ブラウザでノートブック作成・文書追加・Q&A実行

---

### 8. MiniGame Factory — Port 3100 (UI) / 8100 (API)

- **用途**: SpecJSONからHTML5ゲーム・Android APK自動生成
- **ブラウザURL**: `$BROWSER_MINIGAME_URL` (<http://host.docker.internal:3100>)
- **内部API**: `$MINIGAME_API_URL` (http://minigame_api:8000)
- **API操作例**:

  ```bash
  # プロジェクト一覧
  curl "$MINIGAME_API_URL/projects"
  # ゲームビルド実行
  curl -X POST "$MINIGAME_API_URL/build" -H "Content-Type: application/json" -d '{...}'
  ```

---

### 9. IATF System (Rails) — Port 3000

- **用途**: IATF 16949コンプライアンス・品質文書管理
- **ブラウザURL**: `$BROWSER_IATF_URL` (<http://host.docker.internal:3000>)
- **操作**: ブラウザでRailsアプリを操作

---

### 10. Stirling PDF — Port 8085

- **用途**: PDF操作（結合・分割・変換・OCR）
- **ブラウザURL**: `$BROWSER_STIRLING_PDF_URL` (<http://host.docker.internal:8085>)
- **操作**: ブラウザUIでPDFをアップロードして操作

---

### 11. AI Art Studio (Stable Diffusion) — Port 7861

- **用途**: AI画像生成・写真修復・着色
- **ブラウザURL**: `$BROWSER_STABLE_DIFFUSION_URL` (<http://host.docker.internal:7861>)
- **内部API**: `http://host.docker.internal:7861/sdapi/v1` (SD WebUI API)
- **API操作例**:

  ```bash
  # 画像生成
  curl -X POST "http://host.docker.internal:7861/sdapi/v1/txt2img" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"...", "steps":20, "width":512, "height":512}'
  ```

---

### 12. VoiceVox — Port 50021

- **用途**: 日本語音声合成
- **内部API**: `$BROWSER_VOICEVOX_URL` (<http://host.docker.internal:50021>)
- **API操作例**:

  ```bash
  # 音声クエリ生成
  curl -X POST "$BROWSER_VOICEVOX_URL/audio_query?text=こんにちは&speaker=3"
  # 音声合成
  curl -X POST "$BROWSER_VOICEVOX_URL/synthesis?speaker=3" \
    -H "Content-Type: application/json" -d '<audio_queryの出力>' > audio.wav
  ```

---

### 13. Open WebUI (Premium RAG) — Port 3002

- **用途**: RAG統合チャットUI。SearXNGを通じたWeb検索と、社内Qdrant知識検索を組み合わせて高度な回答を生成。
- **ブラウザURL**: `http://host.docker.internal:3002`
- **操作**: ブラウザ経由でドキュメントのアップロードや検索。AIエージェントの操作ハブとして機能。

---

### 14. SearXNG (Web Search Proxy) — Port 8086

- **用途**: Web検索APIプロキシ。
- **内部URL**: `$SEARXNG_URL` (<http://searxng:8080>)
- **操作**: OpenAPI仕様で検索。Open WebUIや他のエージェントスクリプトから呼び出し。

---

### 15. LiteLLM (LLM Gateway) — Port 4000

- **用途**: 複数LLMプロバイダの統合管理、キャッシュ、APIキー管理。
- **内部URL**: `$LITELLM_URL` (<http://litellm:4000>)
- **操作**: `LITELLM_MASTER_KEY` を使用してOpenAI互換APIでアクセス。

---

### 16. Figma Design Specs & Protocol (Design-to-Code)

- **用途**: Figma MCP経由で抽出したデザイン定義（JSON）および実装ルールの管理。
- **保存パス**: `/home/node/clawd/docs/figma/`
- **操作**:
  - `figma_mcp_protocol_v1_0.md` に基づき、Codexで仕様抽出・保存。
  - 保存された `variables.json` や `design_rules.md` を読み取り、OpenClawで実装。

---

### 17. Local HTML Apps (ポータル内 apps/ ディレクトリ)

- Tolerance Center: `http://host.docker.internal:8088/apps/tolerance_hub/index.html`
- Injection Molding Hub: `http://host.docker.internal:8088/apps/molding_hub/index.html`
- AI Video Factory: `http://host.docker.internal:8088/apps/video_factory/index.html`
- Note Pro Writer: `http://host.docker.internal:8088/apps/note_pro/index.html`
- Kindle Author: `http://host.docker.internal:8088/apps/kindle_author/index.html`
- Kinematics Hub: `http://host.docker.internal:8088/apps/kinematics_hub/index.html`
- OpenRadioss Hub: `http://host.docker.internal:8088/apps/radioss_hub/index.html`

---

## CLIツール（コンテナ内で直接実行）

### OpenFOAM (CFD)

```bash
docker exec clawstack-unified-openfoam-1 sh -c "source /opt/openfoam*/etc/bashrc && blockMesh && simpleFoam"
```

### OpenRadioss (Crash)

```bash
docker exec clawstack-unified-openradioss-1 starter -i input.rad
docker exec clawstack-unified-openradioss-1 engine -i input_0001.rad
```

### CalculiX (FEA) — clawdbot-gateway コンテナ内に直接インストール済み

```bash
ccx input_file
```

### ElmerFEM

```bash
ElmerSolver case.sif
```

### Python科学計算 — clawdbot-gateway コンテナ内

```bash
python3 /home/node/clawd/scripts/your_script.py
```

---

## インフラサービス（エージェントが直接利用）

| サービス | 内部URL | 用途 |
|---|---|---|
| Ollama | `$OLLAMA_URL` | LLM推論 |
| Qdrant | `$QDRANT_URL` | ベクトルDB |
| MinIO | `$MINIO_URL` | オブジェクトストレージ |
| PostgreSQL | `$POSTGRES_URL` | リレーショナルDB |
| Redis | `$REDIS_URL` | キャッシュ/キュー |

---

## 操作の優先順位

1. **REST API** が利用可能な場合は API 優先（高速・確実）
2. API がない場合は **ブラウザ操作** (`openclaw browser navigate/snapshot/click/type`)
3. CLIツールは **docker exec** または直接実行
