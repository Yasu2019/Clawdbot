# SYSTEM_FACTS.md - システム現状と確定事項

> **目的:** このファイルは、ClawdBotおよびAntigravityが「現在のシステム状態」を正確に把握し、ユーザーに何度も同じ説明を求めないための「長期記憶」として機能します。
> **ルール:** 何か回答する前や提案する前に、必ずこのファイルを確認し、**「すでに実装済みの機能」を「まだない」と誤認しないようにしてください。**

---

## 🏗️ 実装済みシステム構成

### 1. ローカルLLM (Ollama)

- **ステータス:** ✅ 実装済み・稼働中
- **ホスト:** Windowsホストマシン (`host.docker.internal:11434`)
- **使用モデル:**
  - `llama3:8b` (デフォルト)
  - `deepseek-r1:7b`
- **ClawdBotからの接続:** Dockerコンテナから環境変数 `OLLAMA_BASE_URL` 経由で接続済み。

### 2. Google Drive 連携

- **ステータス:** ✅ 実装済み
- **同期ツール:** `rclone` (コンテナ内インストール済み)
- **バックアップ対象:**
  - API Logs (`ClawdBot_Logs/API_Usage_Log`)
  - PROMISES.md (`ClawdBot_Logs/PROMISES.md`)
  - Obsidian Vault 全体 (`ClawdBot_Vault_Backup`)
- **自動化:** `sync_to_gdrive.sh` により実行可能

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
