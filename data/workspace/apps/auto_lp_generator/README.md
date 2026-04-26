# OpenClaw 完全統合版 Auto LP Generator

品質保証・製造DX・IATF資料・顧客説明資料向けの LP / Web資料を自動生成する OpenClaw 統合パッケージです。

## 目的
- ChatGPT Image 2 / Claude Design / Claude Code / Antigravity / Codex CLI を組み合わせた LP制作フローを OpenClaw Portal に統合
- 品質ダッシュボード、IATF内部監査説明、工程可視化、顧客向け技術紹介ページを短時間で作成
- 既存OpenClaw環境を壊さないため、既定では独立サービスとして起動

## 既定ポート
- Auto LP API: http://127.0.0.1:8010
- UI: http://127.0.0.1:8010/ui
- Portalカード: portal/apps/auto_lp_generator/index.html

## 起動
```bat
cd D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_auto_lp_generator
copy .env.example .env
docker compose up -d --build
```

## 動作確認
```bat
scripts\healthcheck.bat
scripts\generate_sample.bat
```

## Portal統合
```bat
scripts\install_to_openclaw_portal.bat
```

## AI連携方式
- AI_MODE=local_template: ローカルテンプレ生成
- AI_MODE=manual_image2_claude: Image2とClaude Designの手動成果物を取り込み
- AI_MODE=litellm: OpenClaw LiteLLM Proxy経由で構成案生成

## 注意
既存Docker Composeを直接編集しません。docs/INTEGRATION_CHECKLIST.md に従い、Codex / Claude / Antigravityに差分確認させてから統合してください。
