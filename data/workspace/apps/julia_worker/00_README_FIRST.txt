Clawstack Julia Numerical Worker 完全統合 本気版ZIP
==================================================

目的:
  既存の Clawstack / OpenClaw / Portal / Node-RED / FastAPI 構成を壊さず、
  Julia を「高速数値計算専用Worker」として追加します。

重要:
  - 既存 docker-compose.yml を直接書き換えないでください。
  - まず Git バックアップを取ってください。
  - 単独テスト → override統合 → Portalカード追加 の順で進めてください。
  - JuliaはPython置換ではなく、DOE/最適化/CAE補助/数値計算用です。

最初に読む順番:
  1. docs/SAFETY_GUARDRAILS.md
  2. docs/INTEGRATION_POLICY.md
  3. README.md
  4. docs/OPERATIONS_RUNBOOK.md
  5. prompts/CODEX_IMPLEMENTATION_PROMPT.md

推奨導入順:
  1. このZIPを Clawstack のルート直下へ展開
  2. scripts/git_safe_backup.ps1 または .sh を実行
  3. docker-compose.julia-worker.standalone.yml で単独起動テスト
  4. docker-compose.julia-worker.override.example.yml を参考に既存composeへ追加
  5. Portalカードを追加
  6. Node-RED / OpenClaw から HTTP API として呼び出し

Windows PowerShell例:
  cd C:\path\to\clawstack-unified
  powershell -ExecutionPolicy Bypass -File .\scripts\git_safe_backup.ps1
  docker compose -f docker-compose.julia-worker.standalone.yml up --build

WSL/Linux例:
  cd ~/clawstack-unified
  bash scripts/git_safe_backup.sh
  docker compose -f docker-compose.julia-worker.standalone.yml up --build

動作確認:
  PowerShell:
    Invoke-RestMethod http://localhost:8096/health

  curl:
    curl http://localhost:8096/health

生成日:
  2026-04-29

文字コード:
  UTF-8
