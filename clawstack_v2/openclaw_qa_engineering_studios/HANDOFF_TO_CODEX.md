# HANDOFF_TO_CODEX.md

## Codex CLIへの依頼

このZIPを `D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios` に展開し、既存OpenClaw構成と衝突しないか確認してください。

## 必ず守ること

- 既存ファイルを上書きする前に差分を提示すること
- SQL Serverへの書き込み処理を追加しないこと
- docker-compose のポート衝突を確認すること
- Portalカード追加時は既存 `PORTAL_APPS.md` と照合すること
- 作業の前後で `ACT.md` を更新すること

## 推奨コマンド

```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios
python scripts\run_review.py --mode full --root ..
```
