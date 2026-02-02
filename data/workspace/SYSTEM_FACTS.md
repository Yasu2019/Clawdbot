# SYSTEM_FACTS.md - システム現状と確定事項

> **目的:** このファイルは、ClawdBotおよびAntigravityが「現在のシステム状態」を正確に把握し、ユーザーに何度も同じ説明を求めないための「長期記憶」として機能します。
> **ルール:** 何か回答する前や提案する前に、必ずこのファイルを確認し、**「すでに実装済みの機能」を「まだない」と誤認しないようにしてください。**

---

## 🏗️ 実装済みシステム構成

### 1. ローカルLLM (Ollama)

- **ステータス:** ✅ 実装済み・稼働中
- **ホスト:** Windowsホストマシン (`host.docker.internal:11434`)
- **Models:**
  - `llama3:8b` (Default)
  - `deepseek-r1:7b` / `32b`
  - `qwen2.5:7b` / `1.5b`
  - `gemma2:27b` / `gemma3:27b`
  - `llama3.1` / `3.2` / `3.3`
  - `phi3:mini` / `phi4`
  - `gpt-oss:20b` / `120b-cloud`
  - (その他: `ChatMusician`, `lfm2.5` 等)
- **ClawdBotからの接続:** Dockerコンテナから環境変数 `OLLAMA_BASE_URL` 経由で接続済み。

### 2. Gmail / Calendar 連携

- **ステータス:** ✅ 実装済み・稼働中
- **スクリプト:** `data/workspace/scripts/gmail_to_calendar.js`
- **頻度:** 毎時 (Cron: `0 * * * *`)
- **アクション:** 未読メール解析(Gemini) → カレンダー登録
- **認証:** 完了 (App Published / No 7-day limit)
- **※履歴:** 2026/02/02 Error 429発生 → ゾンビプロセス(curl)停止により解決。

### 3. Google Drive 連携

- **ステータス:** ✅ 実装済み
- **同期ツール:** `rclone` (コンテナ内インストール済み)
- **バックアップ対象:**
  - API Logs (`ClawdBot_Logs/API_Usage_Log`)
  - PROMISES.md (`ClawdBot_Logs/PROMISES.md`)
  - Obsidian Vault 全体 (`ClawdBot_Vault_Backup`)
- **自動化:** `sync_to_gdrive.sh` により実行可能

### ✅ Network Isolation

- **Gateway Port:** `127.0.0.1:18789` (Localhost access only)
- **Effect:** 外部インターネットからの直接攻撃を遮断

### 4. Work Log System (Long-term Memory)

- **Status:** ✅ Implemented
- **Format:** `04_System_Records/Templates/WORK_LOG_TEMPLATE.md`
- **Location:** `03_Logs/Work_Logs/`
- **Sync:** Auto-synced to Google Drive via `ClawdBot_Vault_Backup`

## 🔒 セキュリティ対策状況 (2026-02-02実施)

| リスク項目 | 対策状況 | 詳細 |
|---|---|---|
| **過剰な権限** | ✅ 対応済 | Dockerコンテナ内で隔離実行。ホストへの影響は限定的。 |
| **外部への露出** | ✅ 対応済 | `127.0.0.1` 結合により外部アクセスを物理的に遮断。 |
| **不正アクセス** | ✅ 対応済 | Telegram `allowFrom` でID指定制限済み。 |
| **データ消失** | ✅ 対応済 | Google Driveへの全量バックアップ稼働中。 |
| **機密情報** | ✅ 対応済 | `.env` で管理し、git/ログからは除外設定済み。 |

### 3. 使用モデル設定 (ClawdBot Gateway)

- **メインモデル:** `google/gemini-2.0-flash`
  - ※ 以前 `1.5-flash` で不具合があったため `2.0-flash` に固定済み。
- **Anthropic:** 使用していない（Google Providerを使用）。

---

## 📝 重要な運用ノウハウ

### メモリ・コンテキスト維持

- **「Ollamaは入っているか？」と疑わないこと。** すでに入っている。
- **「Google Drive連携は必要か？」と聞かないこと。** すでに連携されている。
- ユーザーの環境は **Docker Desktop on Windows** であり、ホスト連携が密に行われている。

### エラー対応履歴

- **404 Model Not Found:** Geminiのモデル名変更時は `.env` ではなく `clawdbot.json` を確認・修正すること。
- **400 Empty Prompt:** モデル設定が正しくない時に発生しやすい。

---
*最終更新: 2026-02-02*
