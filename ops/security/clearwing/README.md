# Clearwing 本気版 ローカル防御パック

このZIPは、**Clearwing を中心にしたローカル脆弱性診断ワークフロー**を、安全策込みで素早く立ち上げるための実務向けパックです。

## 目的
- 外部へ機密コードを出さずに脆弱性診断を行う
- Clearwing / Ollama / Semgrep / Bandit / OWASP ZAP を組み合わせる
- 人間承認（HITL）を前提に危険操作を封じる
- 将来、OpenClaw / n8n / Codex / Claude Code へ受け渡しやすい構成にする

## 同梱内容
- docs/00_EXEC_SUMMARY_ja.md
- docs/01_IMPLEMENTATION_PROTOCOL_ja.md
- docs/02_CLAUDE_CODE_PROTOCOL_ja.md
- docs/03_CODEX_PROTOCOL_ja.md
- docs/04_SECURITY_GUARDRAILS_ja.md
- docs/05_VALIDATION_CHECKLIST_ja.md
- docker/docker-compose.yml
- configs/.env.example
- scripts/bootstrap.sh
- scripts/run_static_scan.sh
- scripts/run_zap_baseline.sh
- templates/report_template.md

## 想定構成
- LLM: Ollama
- AI脆弱性探索: Clearwing
- 静的解析: Semgrep / Bandit
- 動的確認: OWASP ZAP baseline
- オーケストレーション: 今回は簡易スクリプト。将来 n8n / OpenClaw に移植しやすいように整理済み

## 重要
このパックは**防御・検証目的**です。第三者システムへの無断診断や、許可のない侵入テストに使わないでください。
