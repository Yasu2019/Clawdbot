# 導入手順（推奨順）

## Phase 0: 事前確認
- Node.js 20 以上
- pnpm 9.15 以上
- Docker Desktop / WSL2 が既に安定稼働
- 既存の OpenClaw / LiteLLM / n8n のポート使用状況を確認

### Windows PowerShell
```powershell
netstat -ano | findstr :3100
netstat -ano | findstr :3110
node -v
pnpm -v
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

## Phase 1: 単体検証（最小）
### パターンA: いちばん早い起動
```powershell
npx paperclipai onboard --yes
```

### パターンB: 明示ポート運用（推奨）
Paperclip の標準は 3100 だが、既存構成との衝突回避のため、
このプロトコルではコンテナ外公開ポートを 3110 にする。

## Phase 2: Docker overlay で上乗せ
- 既存 compose を直接書き換えず、overlay compose を追加
- Paperclip 単独 service として切り出す
- まずは local only バインド

## Phase 3: BYOA 登録
最低限以下を登録対象にする。
- OpenClaw
- Claude Code
- Codex CLI
- Antigravity

## Phase 4: 予算と heartbeat を有効化
初期値は小さく始める。
- Claude Code: 月 10
- Codex: 月 10
- Antigravity: 月 5
- OpenClaw continuous runner: 月 15

## Phase 5: 承認ゲートを有効化
以下は human approval 推奨。
- 本番ファイル削除
- compose 更新
- DB schema 変更
- 外部送信（メール、Webhook、Git push）

## Phase 6: 観測と通知
- 重大停止: n8n 通知
- 予算到達 80%: n8n 通知
- heartbeat miss: n8n 通知
