# AI最新リポジトリ 完全実装版パック
作成日: 2026-04-11
文字コード: UTF-8
主目的: Codex / Claude / Antigravity にそのまま渡して、導入可否判定と最小PoCを開始できる状態にする

## 同梱物
- 00_README.md
- 01_全体方針.md
- 02_導入判定プロトコル_完全版.md
- 03_実装アーキテクチャ.md
- 04_段階導入ロードマップ.md
- 05_運用ルール.md
- docker-compose.example.yml
- env.example
- prompts/ai_judge_prompt.txt
- prompts/poc_executor_prompt.txt
- templates/evaluation_sheet.md
- templates/skill_review_template.md
- app/archon_harness.py
- app/hermes_learning_loop.py
- app/skill_registry.py
- app/log_schema.json
- app/sample_tasks.json
- scripts/run_archon_demo.bat
- scripts/run_archon_demo.sh

## このパックの思想
このパックは「最新技術を全部採用する」ためのものではありません。
むしろ逆で、**危険なものを先に落とし、安全に価値が出るものだけを残す**ための実装版です。

## 最重要順序
1. Archon的な再現性ハーネス
2. Hermes的な学習候補生成
3. Vox-CP2 の価値検証

## 想定ユーザー
- Codex CLI
- Claude Code
- Antigravity
- OpenClaw系ローカル運用環境

## 重要
このパックには、すぐ本番投入してよいと断定するコードは含めていません。
含めているのは、**安全側に倒した最小PoCの土台**です。
