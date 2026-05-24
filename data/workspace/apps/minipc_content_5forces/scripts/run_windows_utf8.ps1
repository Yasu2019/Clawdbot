# MiniPC Content 5-Forces Gate - Windows UTF-8 runner
$ErrorActionPreference = "Stop"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== MiniPC Content 5-Forces Gate ==="
Write-Host "UTF-8 mode enabled."

if (!(Test-Path ".venv")) {
    Write-Host "Creating .venv ..."
    py -3 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r backend\requirements.txt

Write-Host ""
Write-Host "Running sample CSV evaluation..."
python cli\evaluate_idea.py --csv data\sample_ideas_utf8.csv --output data\sample_ideas_scored_excel_safe.csv

Write-Host ""
Write-Host "Starting API server at http://localhost:18766"
Write-Host "Stop with Ctrl+C"
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18766
