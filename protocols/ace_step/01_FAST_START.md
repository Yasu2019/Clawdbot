# FAST START

## 1. 前提
- Windows 11
- Docker Desktop (WSL2 backend)
- Ubuntu on WSL2
- Python 3.11 系推奨
- Git
- NVIDIA GPU がある場合は最新ドライバ

## 2. 推奨フォルダ
- `D:\Clawdbot_Docker_20260125\ace_step_stack`

## 3. 実行順
1. 管理者 PowerShell で `scripts/bootstrap_windows_full.ps1`
2. Ubuntu WSL で `bash scripts/bootstrap_wsl_full.sh`
3. 必要に応じて `configs/.env.example` を `.env` にコピーして編集
4. ComfyUI 単体起動: `scripts/launch_comfyui_windows.ps1`
5. Docker 起動: `scripts/launch_stack_docker.ps1`
6. `docs/05_VALIDATION_CHECKLIST.md` で動作確認

## 4. まず試すべき方針
- GPU がまだ無い → ComfyUI 単体で検証
- eGPU 導入後 → Docker 連携に進む
- Clawstack 連携したい → `docs/06_CLAWSTACK_PORTAL_INTEGRATION.md` を読む
