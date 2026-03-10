# OPENCLAW UNIVERSAL ACCESS PROTOCOL (UAP-2026)

> **Version:** 1.0  
> **Date:** 2026-02-23  
> **Purpose:** OpenClaw (Docker Container AI) がシステム全体にアクセスし操作するための統一プロトコル

---

## 1. アーキテクチャ概要

```
┌────────── Windows Host (Brawn) ──────────────────────────────┐
│                                                               │
│  D:\Clawdbot_Docker_20260125\                                │
│  ├── data\workspace\        ← Portal, Apps, Scripts          │
│  │   ├── portal.html        ← Master Portal                 │
│  │   ├── apps\              ← 各種Hub (radioss, molding...) │
│  │   ├── scripts\           ← Gmail/Calendar/Billing         │
│  │   ├── docs\              ← プロトコル・ルール MD          │
│  │   └── projects\          ← プロジェクトデータ             │
│  └── clawstack_v2\                                           │
│      ├── data\work\         ← /work (共有ワークディレクトリ) │
│      ├── data\paperless\    ← Paperless 文書管理             │
│      ├── secrets\           ← Google認証・通知設定           │
│      └── docker-compose.yml ← 全サービス定義                 │
│                                                               │
│  ┌─────────── Docker Network (clawstack) ───────────┐       │
│  │                                                    │       │
│  │  antigravity (Brain)  ← OpenClaw本体               │       │
│  │    /work          → data/work                      │       │
│  │    /secrets       → secrets (RO)                   │       │
│  │    /home/node/paperless/consume → paperless/consume│       │
│  │                                                    │       │
│  │  google_worker    ← Gmail/Calendar/Drive操作       │       │
│  │    /work, /secrets                                 │       │
│  │                                                    │       │
│  │  portal_server    ← nginx:8088 (Portal配信)        │       │
│  │  paperless        ← :8000 (文書OCR/検索)           │       │
│  │  ollama           ← :11434 (ローカルLLM)           │       │
│  │  postgres/redis/qdrant/minio  ← データ基盤         │       │
│  └────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. ファイルシステムアクセス

### 2.1 OpenClaw (Docker内) からのパスマッピング

| Docker内パス | ホスト実体 | 用途 |
|---|---|---|
| `/work/` | `clawstack_v2/data/work/` | 共有ワークディレクトリ (auth.json含む) |
| `/secrets/` | `clawstack_v2/secrets/` | Google認証、通知設定 (読取専用) |
| `/home/node/paperless/consume/` | `clawstack_v2/data/paperless/consume/` | Paperless取込フォルダ |

### 2.2 ルール・ノウハウ MD ファイルアクセス

```bash
# Docker内から直接アクセス不可 → /workにコピーするか、portal_serverのHTTP経由で取得
# 推奨方法: portal_server (nginx:8088) を利用

curl http://portal_server/docs/CLAWDBOT_OPERATIONAL_GUIDE.md
curl http://portal_server/docs/DUAL_AGENT_PROTOCOL.md
curl http://portal_server/docs/HOST_TOOLS_MANUAL.md
```

現在の利用可能プロトコル MD:

| ファイル | 内容 |
|---|---|
| `CLAWDBOT_OPERATIONAL_GUIDE.md` | Brain & Brawn基本運用ガイド |
| `DUAL_AGENT_PROTOCOL.md` | Antigravity + Clawdbot 役割分担 |
| `HOST_TOOLS_MANUAL.md` | Windows側ツール (Elmer/ParaView/Blender/Unity) |
| `OPENRADIOSS_AUTONOMY_PROTOCOL.md` | OpenRadioss自律実行手順 |
| `THREEJS_AUTONOMY_PROTOCOL.md` | Three.js WebGL可視化 |
| `UNITY_AUTONOMY_PROTOCOL.md` | Unity BatchMode |
| `BLENDER_AUTONOMY_PROTOCOL.md` | Blender headless渲染 |
| `ELMER_WORKFLOW_GUIDE.md` | ElmerFEMソルバー |
| `OPENCLAW_UNIVERSAL_ACCESS_PROTOCOL.md` | **本ドキュメント** |

### 2.3 Paperless Consume アクセス

```bash
# ドキュメント取込 (Docker内から直接)
cp /work/reports/quality_report.pdf /home/node/paperless/consume/

# サブディレクトリ → 自動タグ化 (PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS=true)
cp report.pdf /home/node/paperless/consume/5Why_Analysis/

# Paperless API (OCR済みドキュメント検索)
curl http://paperless:8000/api/documents/?query=5Why
```

---

## 3. Google Workspace 操作

### 3.1 認証セットアップ

**前提条件:**

1. Google Cloud Console で OAuth 2.0 クライアント ID を作成
2. `credentials.json` を `/secrets/google_credentials.json` に配置
3. 初回認証で `token.json` が `/secrets/google_token.json` に生成

```bash
# google_workerコンテナでの認証 (初回のみホスト側ブラウザ必要)
docker exec -it clawstack-google_worker-1 python3 /work/scripts/setup_google_auth.py
```

### 3.2 Gmail 操作

| 操作 | コマンド / API |
|---|---|
| **メール送信** | `docker exec google_worker python3 /work/scripts/send_gmail.py --to "addr" --subject "件名" --body "本文"` |
| **メール一覧** | `docker exec google_worker python3 /work/scripts/list_gmail.py --query "is:unread" --max 10` |
| **添付ファイル取得** | `docker exec google_worker python3 /work/scripts/download_attachment.py --msg-id "ID" --out /work/downloads/` |
| **ラベル管理** | `docker exec google_worker python3 /work/scripts/manage_labels.py --add "Clawdbot/Processed"` |

**notification.json による簡易送信 (SMTPモード):**

```python
import json, smtplib
from email.mime.text import MIMEText

with open('/secrets/notification.json') as f:
    cfg = json.load(f)

msg = MIMEText('本文')
msg['Subject'] = '件名'
msg['From'] = cfg['gmail_user']
msg['To'] = 'recipient@example.com'

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login(cfg['gmail_user'], cfg['gmail_app_password'])
    s.send_message(msg)
```

### 3.3 Google Calendar 操作

| 操作 | コマンド |
|---|---|
| **予定一覧** | `docker exec google_worker python3 /work/scripts/list_events.py --days 7` |
| **予定作成** | `docker exec google_worker python3 /work/scripts/create_event.py --title "会議" --start "2026-02-24T10:00" --end "2026-02-24T11:00"` |
| **予定更新** | `docker exec google_worker python3 /work/scripts/update_event.py --event-id "ID" --title "変更後"` |
| **予定削除** | `docker exec google_worker python3 /work/scripts/delete_event.py --event-id "ID"` |

**API直接利用:**

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('/secrets/google_token.json')
service = build('calendar', 'v3', credentials=creds)

# 今後7日間の予定取得
events = service.events().list(
    calendarId='primary',
    timeMin='2026-02-23T00:00:00+09:00',
    maxResults=20, singleEvents=True, orderBy='startTime'
).execute()
```

### 3.4 Google Drive 操作

| 操作 | コマンド |
|---|---|
| **ファイル一覧** | `docker exec google_worker python3 /work/scripts/list_drive.py --folder "Clawdbot"` |
| **アップロード** | `docker exec google_worker python3 /work/scripts/upload_drive.py --file /work/reports/report.pdf --folder-id "FOLDER_ID"` |
| **ダウンロード** | `docker exec google_worker python3 /work/scripts/download_drive.py --file-id "FILE_ID" --out /work/downloads/` |
| **共有設定** | `docker exec google_worker python3 /work/scripts/share_drive.py --file-id "FILE_ID" --email "user@example.com"` |

**API直接利用:**

```python
from googleapiclient.http import MediaFileUpload

service = build('drive', 'v3', credentials=creds)

# アップロード
media = MediaFileUpload('/work/reports/report.pdf', mimetype='application/pdf')
file = service.files().create(
    body={'name': 'report.pdf', 'parents': ['FOLDER_ID']},
    media_body=media
).execute()

# ダウンロード
request = service.files().get_media(fileId='FILE_ID')
with open('/work/downloads/file.pdf', 'wb') as f:
    f.write(request.execute())
```

---

## 4. Master Portal アプリアクセス

### 4.1 ポータル経由 HTTP アクセス

Portal Server (`nginx:8088`) が `data/workspace/` を配信:

| アプリ | URL (Docker内) | 概要 |
|---|---|---|
| **Master Portal** | `http://portal_server/portal.html` | 全アプリのハブ |
| **OpenRadioss Hub** | `http://portal_server/apps/radioss_hub/index.html` | 衝突・プレス解析GUI |
| **Molding Hub** | `http://portal_server/apps/molding_hub/index.html` | 射出成形DOE |
| **Tolerance Hub** | `http://portal_server/apps/tolerance_hub/index.html` | 公差解析 |
| **MiniGame Factory** | `http://portal_server/apps/minigame_factory/` | ゲーム工場 |

### 4.2 Docker内サービスへの直接アクセス

| サービス | Docker内URL | ポート(Host) | 概要 |
|---|---|---|---|
| **Paperless-ngx** | `http://paperless:8000` | `:8000` | 文書OCR・全文検索 |
| **Draw.io** | `http://drawio:8080` | `:8081` | ダイアグラム作成 |
| **n8n** | `http://n8n:5678` | `:5679` | ワークフロー自動化 |
| **Node-RED** | `http://nodered:1880` | `:1880` | IoTフロー |
| **Open Notebook** | `http://open_notebook:8502` | `:8502` | ローカルNotebookLM |
| **Ollama** | `http://ollama:11434` | `:11434` | ローカルLLM |
| **Qdrant** | `http://qdrant:6333` | `:6333` | ベクトルDB |
| **MinIO** | `http://minio:9000` | `:9000/9001` | S3互換ストレージ |
| **MeiliSearch** | `http://meilisearch:7700` | `:7700` | 全文検索 |
| **Stirling PDF** | `http://stirling_pdf:8080` | `:8085` | PDF編集 |
| **VOICEVOX** | `http://voicevox:50021` | `:50021` | 音声合成 |
| **Quality Dashboard** | `http://quality_dashboard:8090` | `:8090` | 品質管理 |
| **WorkStudy AI** | `http://workstudy_app:7870` | `:7870` | 作業分析 |

### 4.3 CAEソルバー (profiles=cae)

| サービス | 用途 | Docker内実行 |
|---|---|---|
| **OpenRadioss** | 衝突・プレス解析 | `docker exec openradioss /opt/openradioss/exec/starter_linux64_gf` |
| **OpenFOAM** | CFD | `docker exec openfoam simpleFoam` |
| **Project Chrono** | マルチボディ | `docker exec chrono python3 script.py` |

---

## 5. 操作フローマトリクス

```mermaid
flowchart LR
    subgraph OpenClaw["OpenClaw (antigravity)"]
        A[タスク受信] --> B{操作種別}
    end

    B -->|"📧 Gmail"| G[google_worker exec]
    B -->|"📅 Calendar"| G
    B -->|"📁 Drive"| G
    B -->|"📄 Paperless取込"| P[cp → /home/node/paperless/consume/]
    B -->|"🌐 Portal App"| W[curl http://portal_server/...]
    B -->|"📝 ルールMD読込"| W
    B -->|"🔧 CAEソルバー"| S[docker exec openradioss/openfoam]
    B -->|"🤖 ローカルLLM"| O[curl http://ollama:11434/api/generate]
    B -->|"🔍 文書検索"| M[curl http://meilisearch:7700/indexes/...]
    B -->|"💾 ファイル保存"| F[/work/ 直接書込]
    B -->|"🖥️ Windows専用"| H["User実行依頼 (Blender/Unity/Elmer)"]

    G --> R[結果を /work/ に保存]
    P --> R
    S --> R
    F --> R
```

---

## 6. セキュリティ規則

1. **認証情報**: `/secrets/` は読取専用。トークンの外部送信禁止
2. **外部通信**: `127.0.0.1` バインド → Docker外からアクセス不可
3. **ファイル削除**: `/work/` 内のみ可。ルートファイルシステムの変更禁止
4. **Gmail操作**: 送信は事前にユーザー承認を取得。自動送信は日次レポートのみ許可
5. **Drive操作**: 共有設定変更にはユーザー承認必須

---

## 7. 初期セットアップ チェックリスト

```bash
# 1. Google OAuth 認証 (初回のみ)
# ホスト側でブラウザ認証後、token.jsonが生成される
docker compose --profile tools up -d google_worker
docker exec -it clawstack-google_worker-1 python3 setup_google_auth.py

# 2. notification.json の設定
# secrets/notification.json に Gmail App Password を記入

# 3. Paperless 初期化
docker compose --profile docs up -d paperless
# http://127.0.0.1:8000 で admin/admin ログイン

# 4. Portal Server 起動
docker compose --profile tools up -d portal_server
# http://127.0.0.1:8088/portal.html で確認

# 5. 全プロファイル一括起動
docker compose --profile tools --profile cae --profile docs --profile quality up -d
```

---

## 8. 参照ドキュメント

| ドキュメント | パス |
|---|---|
| 本プロトコル | `docs/OPENCLAW_UNIVERSAL_ACCESS_PROTOCOL.md` |
| 運用ガイド | `docs/CLAWDBOT_OPERATIONAL_GUIDE.md` |
| Dual Agent | `docs/DUAL_AGENT_PROTOCOL.md` |
| ホストツール | `docs/HOST_TOOLS_MANUAL.md` |
| docker-compose | `clawstack_v2/docker-compose.yml` |
| 認証設定 | `clawstack_v2/data/work/auth.json` |
| 通知設定 | `clawstack_v2/secrets/notification.json` |

---
*Established by Antigravity for OpenClaw Universal System Access*
