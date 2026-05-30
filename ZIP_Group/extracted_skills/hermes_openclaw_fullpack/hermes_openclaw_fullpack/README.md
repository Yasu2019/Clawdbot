# Hermes Agent × OpenClaw 品質保証向け統合検証パック

目的: Hermes Agent をミニPC / OpenClaw / Portal / Ollama 環境へ安全に統合するための、文字化けしにくい UTF-8 構成サンプルです。

## 重要方針

- 会社情報、図面、Gmail本文、顧客情報は外部LLMへ送らない
- まず WSL2 + Docker + 専用workspace で検証する
- 本番フォルダ、既存DB、既存Docker volume は直接触らない
- 破壊的コマンドは safety_harness でブロックする
- Codex / Claude Code はこのZIPをレビューし、採用可否を判定する

## 含まれるもの

- docker-compose.hermes-openclaw.yml
- Hermes Bridge FastAPI サンプル
- Safety Harness サンプル
- QA Memory API サンプル
- MCP tool manifest サンプル
- Portal card JSON
- Codex向け受入れ判定プロンプト
- Windows / Linux 起動スクリプト

## 起動イメージ

```bash
cd hermes_openclaw_fullpack
cp .env.example .env
docker compose -f configs/docker-compose.hermes-openclaw.yml up -d --build
```

## 推奨モデル振り分け

| 用途 | 推奨 |
|---|---|
| 機密QA文書 | Ollama / qwen3:8b または qwen3:14b |
| コード生成 | qwen2.5-coder:14b / Codex |
| 公開Web調査 | 外部LLM可 |
| Gmail / 図面 / 顧客情報 | 外部送信禁止 |

## ディレクトリ

```text
configs/          Docker Compose と環境設定
src/              サンプル実装
portal/cards/     Portalカード
scripts/          起動・診断スクリプト
docs/             設計書・運用ルール
codex_prompts/    Codex CLI / Claude Code 向け指示
examples/         QAユースケース例
```
