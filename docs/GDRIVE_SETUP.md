# Google Drive 同期設定手順

## 概要

ClawdBotがGoogle Driveに直接ファイルをアップロードできるようにするための設定手順です。

---

## ステップ1: Dockerイメージの再ビルド

```powershell
cd D:\Clawdbot_Docker_20260125
docker compose build --no-cache clawdbot-gateway
```

---

## ステップ2: rclone設定（ホストPCで実行）

### 2a. rcloneをWindowsにインストール

1. <https://rclone.org/downloads/> からWindows版をダウンロード
2. 解凍して `rclone.exe` をPATHに追加

または PowerShell:

```powershell
winget install Rclone.Rclone
```

### 2b. Google Drive認証

```powershell
rclone config
```

対話式で設定:

1. `n` (new remote)
2. Name: `gdrive`
3. Storage: `drive` (Google Drive)
4. client_id: (空欄でOK)
5. client_secret: (空欄でOK)
6. scope: `1` (Full access)
7. root_folder_id: (空欄でOK)
8. service_account_file: (空欄でOK)
9. Edit advanced config: `n`
10. Use auto config: `y`
11. ブラウザでGoogleにログイン → 許可

### 2c. 設定ファイルをコピー

```powershell
copy "$env:USERPROFILE\.config\rclone\rclone.conf" "D:\Clawdbot_Docker_20260125\data\rclone\"
```

---

## ステップ3: コンテナ再起動

```powershell
docker compose up -d --force-recreate clawdbot-gateway
```

---

## ステップ4: 動作確認

```powershell
docker compose exec clawdbot-gateway rclone listremotes
```

`gdrive:` と表示されればOK!

---

## 使用方法

ClawdBotに以下のように指示:

> 「Obsidianのログを Google Drive に同期して」

ClawdBotは `/home/node/clawd/bin/sync_to_gdrive.sh` を実行します。

---

## NotebookLMでの利用

1. NotebookLM (<https://notebooklm.google.com/>) を開く
2. 「New Notebook」作成
3. 「Add Source」→「Google Drive」
4. `ClawdBot_Logs` フォルダを選択

これでNotebookLMがAPI使用ログを分析可能になります！
