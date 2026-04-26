# Codex CLI Prompt

D:\OpenClaw_ClaudeContext_Protocol を読み、OpenClaw既存構成 D:\Clawdbot_Docker_20260125\clawstack_v2 と衝突しないか確認してください。

実行順:
1. READMEとdocsを読む
2. 既存compose, ports, servicesを調査
3. docker-compose.claude-context.yml の採用可否を判断
4. 必要ならポート変更案をdiffで出す
5. 直接本番composeへ混ぜず、overlayで起動確認
6. MCP設定例をClaude Code / Cursor向けに調整
7. OpenClaw固有の検索テスト項目を作る

成果物:
- adoption_report.md
- conflict_report.md
- final_commands.ps1
- rollback_steps.md
