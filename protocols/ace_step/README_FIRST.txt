ACE-Step 1.5 完全自動化版プロトコル for Suzuki / 2026-04-22

目的:
- Windows 11 + WSL2 + Docker Desktop 環境で、ACE-Step 1.5 と ComfyUI をできるだけ自動で立ち上げる
- 将来の Clawstack / Portal 統合に備えた、実ファイル付きの受け渡しセットにする
- 文字化けしにくい UTF-8 テキスト中心で構成する

重要:
1. この ZIP にモデル重みそのものは含めていません。
2. 公式リポジトリからの clone / download を前提にしています。
3. 実運用前にライセンス、利用条件、商用可否、依存関係を必ず再確認してください。
4. 管理者権限が必要な操作があります。

最短手順:
A. docs/01_FAST_START.md を読む
B. scripts/bootstrap_windows_full.ps1 を管理者 PowerShell で実行
C. scripts/bootstrap_wsl_full.sh を WSL Ubuntu で実行
D. scripts/launch_comfyui_windows.ps1 または scripts/launch_stack_docker.ps1 で起動
E. docs/05_VALIDATION_CHECKLIST.md で確認

想定配置:
- 推奨ルート: D:\Clawdbot_Docker_20260125\ace_step_stack
- ただし別フォルダでも動くように可変化しています

含まれるもの:
- 手順書
- PowerShell / Bash スクリプト
- docker compose テンプレート
- env ひな形
- Portal card スタブ
- ComfyUI 用ワークフロー導入メモ
- Codex / Claude Code / Antigravity 向け依頼書
