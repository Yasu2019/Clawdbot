# OpenClaw Secure Runtime - 本番レベル（監査対応可）

目的: Windows PC上で Claude Code / OpenClaw / MCP / Docker / WSL2 を安全に運用するための、監査説明可能な隔離・制御・証跡パッケージです。

## 想定環境
- Windows 11 Pro
- WSL2 Ubuntu 22.04 / 24.04
- Docker Desktop WSL2 backend
- OpenClaw / Clawstack: `D:\Clawdbot_Docker_20260125` 付近
- Claude Code / Codex / Antigravity 等のAIエージェントを併用

## 同梱物
- `docs/`: 設計書、リスク評価、監査説明資料
- `configs/wsl/`: WSL2隔離設定
- `configs/docker/`: 安全実行用docker composeテンプレート
- `configs/policies/`: AIエージェント運用ポリシー
- `scripts/`: 適用・診断・監査証跡取得スクリプト
- `templates/`: 変更管理・例外申請・監査チェックリスト
- `evidence/`: 証跡保存フォルダ

## 導入の基本方針
1. Windows本体を守るため、AIエージェントを直接PowerShellで動かさない。
2. WSL2でWindowsドライブ自動マウントとInteropを無効化する。
3. AIエージェントはDockerコンテナ内で実行する。
4. `.env` やAPIキーは読み取り専用・最小公開・監査記録付きで扱う。
5. 監査時は `scripts/audit/collect_evidence.sh` と `scripts/windows/collect_windows_evidence.ps1` の出力を提示する。

## 最短導入
WSL内で以下を実行します。

```bash
sudo cp configs/wsl/wsl.conf.secure /etc/wsl.conf
sudo bash scripts/linux/create_agent_user.sh
bash scripts/audit/check_wsl_isolation.sh
```

Windows PowerShell（管理者）でWSL再起動:

```powershell
wsl --shutdown
```

再度WSLに入り、確認:

```bash
bash scripts/audit/check_wsl_isolation.sh
```

## 監査での説明文
「AIエージェントの実行環境をWindows本体からWSL2およびDockerで分離し、Windowsドライブへの自動アクセスとWindows実行ファイル起動を禁止しています。さらに運用ポリシー、例外申請、証跡取得手順を整備し、顧客図面・IATF文書・APIキー等の漏洩リスクを低減しています。」
