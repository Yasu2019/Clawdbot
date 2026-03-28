# Medium / High Risk Notification Policy

Last updated: 2026-03-29 JST

## Current implementation

- Low risk auto-repair:
  - [`auto_repair_allowed.py`](/D:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed.py)
- Medium / high risk notification:
  - [`risk_notification.py`](/D:/Clawdbot_Docker_20260125/data/workspace/risk_notification.py)
- Latest status:
  - [`risk_notification_status.json`](/D:/Clawdbot_Docker_20260125/data/workspace/risk_notification_status.json)

`idle_ingest_maintenance.py` now runs `risk_notification.py` after low-risk auto-repair. Medium / high risk items are notified through Telegram first and Gmail second, with duplicate suppression via `risk_notification_state.json`.

## 方針

中リスク、高リスクは原則として `自動実行より先に通知` します。

## 中リスク

例:
- timeout 延長のような運用条件変更
- CORS や接続先フォールバックの変更
- stale status の強制更新
- nightly 再実行

原則:
- 自動検知
- status JSON に記録
- Telegram と Gmail で通知
- 明示的に許可されたルールだけ自動実行

## 高リスク

例:
- compose の大規模変更
- 常駐サービス停止
- cross-org データ方針変更
- 商用 SDK 導入
- 課金 / API キー / 権限変更

原則:
- 自動検知
- status JSON に記録
- Telegram と Gmail で通知
- 自動修復はしない

## 通知チャネル

- 速報: Telegram
- 記録: Gmail
- ローカル監視: Portal / Learning Memory / Auto Repair Console

## いま自動化している範囲

低リスクのみ:
- `auto_repair_allowed.py`

中リスク以上は、今後このポリシーを前提に段階的に通知連携を足す。
