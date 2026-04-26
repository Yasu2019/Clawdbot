# Clawstack 緊急停止手順書

> このファイルは障害発生時の操作手順です。冷静に上から順に実行してください。

---

## 1. 全自動化の即時停止（最優先）

```powershell
# n8n ワークフロー全停止（n8n コンテナを停止）
docker stop clawstack-unified-n8n-1

# OpenClaw ゲートウェイ停止（AIエージェント停止）
docker stop clawstack-unified-clawdbot-gateway-1
```

---

## 2. 障害分類

| Class | 内容 | 対応優先度 |
|-------|------|-----------|
| A | AIが意図しない書込み・削除を実行 | 最高 |
| B | Telegramブリッジが無応答 | 高 |
| C | Gemini/LiteLLM クォータ超過 | 高 |
| D | コンテナ OOM / 再起動ループ | 高 |
| E | Qdrant / Paperless データ破損疑い | 中 |
| F | n8n ワークフロー暴走 | 中 |

---

## 3. 障害別対処

### Class B: Telegramブリッジ停止

```powershell
# 現在のプロセスを終了して再起動
$pid = Get-Content D:\Clawdbot_Docker_20260125\data\state\telegram_fast\bridge.pid 2>$null
if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
& D:\Clawdbot_Docker_20260125\scripts\start_telegram_fast_bridge.ps1

# ステータス確認
Get-Content D:\Clawdbot_Docker_20260125\data\state\telegram_fast\harness_status.json
```

### Class C: モデルクォータ超過

```powershell
# Gemini クォータ切れの場合 → ローカルモデルへ切り替え
$env:TELEGRAM_FAST_MODEL = "qwen3:8b"
& D:\Clawdbot_Docker_20260125\scripts\start_telegram_fast_bridge.ps1
```

### Class D: OOM / コンテナ再起動ループ

```bash
# 問題コンテナを特定
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# 問題コンテナだけ停止
docker stop <コンテナ名>

# ログ確認後に再起動
docker logs <コンテナ名> --tail=50
docker start <コンテナ名>
```

### Class F: n8n ワークフロー暴走

```bash
# 特定ワークフロー停止 (n8n UI から Active を OFF)
# または n8n 全停止
docker stop clawstack-unified-n8n-1
```

---

## 4. 全システム復旧手順

```bash
# 正常な順序で再起動
docker compose -f D:\Clawdbot_Docker_20260125\docker-compose.yml up -d

# 起動確認（主要サービス）
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "gateway|n8n|litellm|qdrant|paperless"
```

```powershell
# Telegramブリッジ再起動（Dockerと独立して動く）
& D:\Clawdbot_Docker_20260125\scripts\start_telegram_fast_bridge.ps1
```

---

## 5. 監査ログ保全

障害後は以下を保存：

```bash
# コンテナログ
docker logs clawstack-unified-clawdbot-gateway-1 > gateway_$(date +%Y%m%d_%H%M).log
docker logs clawstack-unified-n8n-1 > n8n_$(date +%Y%m%d_%H%M).log

# Telegramブリッジエラーログ
copy D:\Clawdbot_Docker_20260125\data\state\telegram_fast\events.log events_backup_%DATE%.log
```

---

## 6. 健全性確認チェックリスト

復旧後に確認：

- [ ] Telegramでメッセージ送信 → 返信あり
- [ ] `http://localhost:5679` (n8n) アクセスOK
- [ ] `http://localhost:4000/health` (LiteLLM) 200返答
- [ ] `http://localhost:6333/healthz` (Qdrant) OK
- [ ] `http://localhost:8000` (Paperless) アクセスOK
- [ ] AI Harness Monitor (n8n) がアクティブで次回実行予定あり

---

*最終更新: 2026-04-07*
