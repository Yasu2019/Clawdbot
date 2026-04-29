# Clawstack × OpenCode GO 完全統合 本気版

目的: OpenCode GOをClawstack/OpenClawの「外部情報収集・有益性判定・安全な採用候補化・システム反映支援」レイヤーとして統合するための実務テンプレートです。

## 重要方針
- OpenCode GOは主役ではなく、外部情報収集と試行回数を増やす「量産エンジン」として扱う。
- 機密図面・顧客名・品質データ・社内文書は原文投入しない。
- 有益情報でも自動本番反映は禁止。必ず `候補化 → 差分確認 → GitHubバックアップ → 人間承認 → 適用` の順にする。
- ローカルLLM優先、OpenCode GOは低コスト外部推論、GPT/Claudeは最終レビュー・危険変更判定に使う。

## 推奨構成
```
Portal / OpenClaw
  ↓
LiteLLM Proxy
  ↓
Policy Router
  ├─ Local Ollama: Qwen/Gemma/DeepSeek local
  ├─ OpenCode GO: Kimi/GLM/DeepSeek V4/Qwen Plus等
  └─ Premium Cloud: GPT/Claude for final judgement
```

## ディレクトリ
- `docs/`: 導入・運用・安全設計ドキュメント
- `configs/`: LiteLLM / n8n / Node-RED向け設定テンプレート
- `portal_card/`: Portalカード追加用HTML/JSON
- `agents/`: 外部情報収集・有益性評価エージェント仕様
- `policies/`: 機密防止・採用可否・変更禁止ポリシー
- `scripts/`: Windows/WSL/Linuxで使う導入補助スクリプト
- `templates/reports/`: 報告書テンプレート
- `examples/`: サンプル入力・出力

## 最初にやること
1. `.env.example` を `.env` にコピー
2. `OPENCODE_GO_API_KEY` を設定
3. `configs/litellm/config.opencode-go.yaml` を既存LiteLLM設定にマージ
4. `policies/` をOpenClaw/Claude/Codex/Gemini向けルールとして読み込ませる
5. Portalへ `portal_card/opencode_go_intel_card.json` を追加

