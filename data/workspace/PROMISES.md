# PROMISES.md - ユーザーとの約束事項

> このファイルは毎日23:00 (JST) に鈴木さんへ送信されます。

---

## 🚨 最重要約束事項

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P017 | **Dockerビルドキャッシュの必須使用:** OpenFOAM・FreeCAD・Paraview・Blender・ElmerFEM等の重量アプリを含むイメージ（特にAntigravity）は、ビルドに30〜60分かかる。コードに破壊的変更がない限り、`docker build` / `docker compose build` 時は必ずキャッシュを使用すること。`--no-cache` の使用は禁止。キャッシュが失われた場合は再作成を優先し、フルビルドを絶対に避ける。API・通信料・時間の大幅な無駄を防ぐため。過去に何度も苦労した経緯がある。 | ✅ 有効 |

---

## 📋 約束事項一覧

### 定期通知

| ID | 約束内容 | 頻度 | 通知先 | ステータス |
|----|---------|------|--------|----------|
| P001 | 約束事項一覧を送信 | 毎日23:00 | Gmail, Telegram | ✅ 有効 (n8n設定待ち) |
| P002 | API使用量レポートを送信 | 1日1回 (08:00 JST) | Telegram | ✅ 有効 |

### Chat動作

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P003 | Chatの最後に使用モデル名を記載 | ✅ 有効 |

### LLM戦略 (Clawstack V3 - Autonomous Delegation Architecture)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P004 | **The Consultant (Host Antigravity):** ホスト側のAntigravityは鈴木さん専用の「相談役・参謀」として振る舞い、直接の作業よりも方針の助言を優先する | ✅ 有効 |
| P005 | **The Coordinator (Container OpenClaw):** コンテナ内のOpenClaw（Gemini Flash）は「現場監督」として振る舞い、軽い受け答えとタスクの進捗管理を行う | ✅ 有効 |
| P006 | **The Internal Specialist (ask_specialist.py):** OpenClawが重いCAEコード生成や高度なデバッグを行う際は、必ず `/work/scripts/ask_specialist.py` を実行してコンテナ内の優秀な推論特化AI（Qwen2.5-Coder:32B）に作業を丸投げ（委任）する | ✅ 有効 |
| P007 | **Cloud Fallback (Codex ChatGPT Plus):** ローカルのSpecialistでも解決できない難解な物理エラー時のみ、最後の手段として定額枠の `ChatGPT Plus` を利用する | ✅ 有効 |

### 自律動作 (Autonomy)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P013 | **IoT監視:** Node-RED/MQTTのデータを定期チェック | ⏸️ 保留 |
| P014 | **CAD設計:** FreeCADを用いて公差解析やモデリングを行う | ✅ 有効 |
| P015 | **自己修復:** エラー発生時は3回まで自律的に修正を試みる | ⏸️ 保留 |
| P016 | **Email報告:** 依頼・QIF・会議の3点セットを毎日まとめ報告 | ✅ 有効 (n8n 毎朝7:00 JST) |

### API使用量抑制 (Cloud使用時)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P008 | 有料API使用時は事前にコスト試算を行う | ✅ 有効 |
| P009 | 定期的なコストレポート提出 | ⏸️ 保留 (一時停止中) |

### Docker ビルドルール

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P017 | **最重要事項を参照** → ページ冒頭の「🚨 最重要約束事項」に詳細記載 | ✅ 有効 |
| P018 | **Antigravity Dockerfile 超細粒度分割:** ダウンロード・展開・インストールを必ず別RUNに分割し、1つのステップが失敗しても前ステップのキャッシュが保全されるよう設計する。特にFreeCAD・OpenFOAM・ElmerFEM・OpenRadioss・PyTorch等の大容量アプリは「DL専用RUN→展開専用RUN→インストール専用RUN」の3分割を徹底する。PythonパッケージとRパッケージは1パッケージ=1RUNとする。合計約60レイヤー構成（2026-03-07実施）。 | ✅ 有効 |
| P019 | **全アプリの再現性保証:** Antigravityに含まれる全アプリ（FreeCAD 0.21.2・OpenFOAM・Blender・CalculiX・Netgen・ElmerFEM・OpenRadioss 20260120・Godot 4.2.1・Rhubarb 1.13.0・Impact FEM・rclone・Remotion等）はDockerfileに完全記録されており、いつでも再現可能。バージョン固定URLを使用。 | ✅ 有効 |

### Clawstack 全サービス インベントリ (P020)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P020 | **全サービスの再現性記録:** 下記インベントリをDockerfileおよびdocker-compose.ymlで管理し、いつでも再構築可能とする | ✅ 有効 |

#### カスタムビルドサービス（Dockerfile管理・再現性高）

| サービス | Dockerfile場所 | 主な内容 |
|---------|--------------|--------|
| **antigravity** | `clawstack_v2/docker/antigravity/Dockerfile` | FreeCAD・OpenFOAM・Blender・ElmerFEM・CalculiX・Netgen・OpenRadioss・Godot・Rhubarb・Impact・rclone・Python/R科学スタック |
| **workstudy_app** | `clawstack_v2/docker/workstudy_app/Dockerfile` | 作業研究AI（姿勢推定・動作分析）|
| **quality_dashboard** | `clawstack_v2/docker/quality_dashboard/Dockerfile` | Streamlit品質ダッシュボード |
| **n8n** | `clawstack_v2/docker/n8n/Dockerfile` | n8nワークフロー（MCP拡張含む）|
| **diagram_cli** | `clawstack_v2/docker/diagram_cli/Dockerfile` | 図形生成CLI |
| **google_worker** | `clawstack_v2/docker/google_worker/Dockerfile` | Googleサービス連携ワーカー |
| **vision_worker** | `clawstack_v2/docker/vision_worker/Dockerfile` | 画像解析ワーカー |
| **openradioss** | `clawstack_v2/docker/openradioss/Dockerfile` | OpenRadioss FEMソルバー |

#### 公式イメージサービス（バージョンタグ管理）

| サービス | イメージ | 用途 |
|---------|---------|-----|
| clawdbot-gateway | カスタムビルド | OpenClaw AIゲートウェイ |
| dify-api / dify-web / dify-worker / dify-plugin-daemon | langgenius/dify-* | Difyワークフローエンジン |
| ollama | ollama/ollama:latest | ローカルLLM |
| paperless | ghcr.io/paperless-ngx/paperless-ngx | 文書管理 |
| n8n | カスタムビルド | ワークフロー自動化 |
| nodered | nodered/node-red | IoT・フロー制御 |
| open_webui | ghcr.io/open-webui/open-webui | LLMチャットUI |
| open_notebook | lfnovo/open_notebook | AIノート |
| qdrant | qdrant/qdrant | ベクトルDB |
| minio | minio/minio | オブジェクトストレージ |
| postgres | postgres:15-alpine | リレーショナルDB |
| redis | redis:alpine | キャッシュ/キュー |
| searxng | searxng/searxng | プライベート検索 |
| voicevox | voicevox/voicevox_engine | 音声合成 |
| litellm | ghcr.io/berriai/litellm:main | LLMプロキシ |
| infinity | michaelf34/infinity | 埋め込みモデルサーバー |
| portal_server | nginx:alpine | ポータルUI |
| label_studio | heartexlabs/label-studio | アノテーション |
| cvat | cvat/cvat_server | 画像ラベリング |
| stable_diffusion | 公式 | 画像生成AI |
| stirling_pdf | stirlingtools/stirling-pdf | PDF処理 |
| meilisearch | getmeili/meilisearch | 全文検索 |
| mosquitto | eclipse-mosquitto | MQTTブローカー |
| drawio | jgraph/drawio | 図形作成 |

### 操作の承認フロー (Human-in-the-Loop)

| ID | 承認レベル | 対象操作 | ステータス |
|----|----------|---------|----------|
| P021 | **[自動実行]** 承認不要 | ログ閲覧・情報検索・ステータス確認・リンター/フォーマット実行・読み取り専用操作 | ✅ 有効 |
| P021 | **[要承認]** Telegramで事前確認 | 依存パッケージの更新・重要な設定ファイルの変更（docker-compose.yml等）・外部サービスへの書き込み・n8nワークフローの変更 | ✅ 有効 |
| P021 | **[禁止]** いかなる場合も実行不可 | 本番DBの削除・アクセス権限の変更・認証情報の外部送信・`--no-cache`ビルド（P017参照） | ✅ 有効 |

---

*ファイル名: `PROMISES.md`*
*保存場所: `data/workspace/PROMISES.md`*
