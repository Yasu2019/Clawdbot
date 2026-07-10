$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-core.txt
& .\.venv\Scripts\python.exe scripts\generate_demo_data.py
& .\.venv\Scripts\python.exe scripts\bootstrap_demo.py
& .\.venv\Scripts\python.exe -m pytest -q
Write-Host "セットアップ完了。windows\run_demo.ps1 を実行してください。"
