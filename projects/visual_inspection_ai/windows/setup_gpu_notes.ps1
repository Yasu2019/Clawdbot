Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "1) nvidia-smi を確認してください。"
nvidia-smi
Write-Host "2) PyTorch公式サイトで現在のCUDA対応コマンドを確認し、.venvへ導入してください。"
Write-Host "3) その後: .\.venv\Scripts\python.exe scripts\gpu_diagnostics.py"
