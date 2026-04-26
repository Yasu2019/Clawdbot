# OpenClaw Integration Guide

## 1. 展開

```powershell
Expand-Archive .\openclaw_qa_engineering_studios.zip -DestinationPath D:\Clawdbot_Docker_20260125\clawstack_v2
```

## 2. 初期レビュー

```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios
python scripts\run_review.py --mode full --root ..
```

## 3. OpenClaw Gatewayへの登録案

OpenClaw Gatewayの既存 `PORTAL_APPS.md`, `SOUL.md`, `TOOLS.md`, `PROMISES.md` を確認し、このテンプレートを参照用ルールセットとして追加する。

## 4. 推奨する導入順

1. ACT.md運用だけ先に導入
2. hooksの安全チェックを導入
3. commandsをCodex/Claude/Antigravity用プロンプトとして導入
4. Portalカード化は最後に実施

## 5. ロールバック

このテンプレートは原則として既存コードを直接変更しない。導入に問題があればフォルダごと削除可能。
