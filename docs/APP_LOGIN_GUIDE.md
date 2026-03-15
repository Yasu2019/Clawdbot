# Clawstack アプリ ログインガイド

**最終更新**: 2026-03-15
**デフォルト管理者**: `admin@clawstack.local` / `clawstack2026`

---

## ログイン済みアプリ一覧

| アプリ | URL | ユーザー名 | パスワード | 備考 |
|---|---|---|---|---|
| **Grafana** | http://localhost:3012 | `admin` | `.env: GRAFANA_ADMIN_PASSWORD` | Prometheus連携済み |
| **Portainer CE** | http://localhost:9002 | `admin` | `.env: CLAWSTACK_ADMIN_PASSWORD` | Docker管理UI |
| **NocoDB** | http://localhost:8093 | `admin@clawstack.local` | `.env: CLAWSTACK_ADMIN_PASSWORD` | DB Spreadsheet |
| **Metabase** | http://localhost:3014 | `admin@clawstack.local` | `.env: CLAWSTACK_ADMIN_PASSWORD` | BIダッシュボード |
| **Uptime Kuma** | http://localhost:3010 | `admin` | `.env: CLAWSTACK_ADMIN_PASSWORD` | 死活監視 |
| **Outline Wiki** | http://localhost:3015 | `admin@clawstack.local` | メールログイン | Mailpitでコード受信 |
| **Langfuse** | http://localhost:3001 | `y.suzuki.hk@gmail.com` | `.env: CLAWSTACK_ADMIN_PASSWORD` | LLMトレース |
| **n8n** | http://localhost:5679 | `y.suzuki.hk@gmail.com` | `.env: n8n_PW` | ワークフロー自動化 |
| **Paperless** | http://localhost:8000 | `admin` | `admin` | ドキュメント管理 |
| **MinIO Console** | http://localhost:9001 | `minioadmin` | `.env: MINIO_ROOT_PASSWORD` | オブジェクトストレージ |

---

## 認証なしアプリ（そのまま使用可）

| アプリ | URL | 用途 |
|---|---|---|
| **SearXNG** | http://localhost:8086 | プライバシー保護検索 |
| **Open WebUI** | http://localhost:3002 | 初回アクセス時にアカウント作成 |
| **Immich** | http://localhost:2283 | 初回アクセス時にアカウント作成 |
| **Whishper** | http://localhost:8098 | 音声文字起こし |
| **LibreTranslate** | http://localhost:5100 | 翻訳API |
| **Dozzle** | http://localhost:8096 | Dockerログ |
| **IT-Tools** | http://localhost:8097 | 開発ユーティリティ |
| **Excalidraw** | http://localhost:3013 | ホワイトボード |
| **Stirling PDF** | http://localhost:8085 | PDF変換・操作 |
| **Prometheus** | http://localhost:9090 | メトリクス |
| **ntfy** | http://localhost:8091 | プッシュ通知 |
| **Mailpit** | http://localhost:8025 | メールテスト受信 |
| **Crawl4AI** | http://localhost:8094 | Webスクレイピング (API) |
| **Meilisearch** | http://localhost:7700 | 全文検索 (APIキー要) |

---

## Outline Wiki ログイン方法

Outline はメール認証方式のため手順が必要です:

1. http://localhost:3015 を開く
2. `admin@clawstack.local` を入力して「メールを送信」
3. http://localhost:8025 (Mailpit) でメールを確認
4. メール内のログインリンクをクリック

---

## Meilisearch APIキー

```
Master Key: (`.env: MEILI_MASTER_KEY` を参照)
API Base: http://localhost:7700
```

---

## セキュリティ注意事項

- 本ファイルにパスワード実値は記載しない（`.env` ファイルを参照）
- `.env` は `.gitignore` により GitHub に公開されない
- 本システムはローカルネットワーク内での使用を前提としています
