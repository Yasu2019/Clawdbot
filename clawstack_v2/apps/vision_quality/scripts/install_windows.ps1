# OpenClaw Vision Quality Inspection - Windows補助スクリプト

$ErrorActionPreference = "Stop"

Write-Host "OpenClaw Vision Quality Inspection setup"

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host ".env を作成しました"
}

docker compose -f docker-compose.vision.yml up -d --build

Write-Host "起動しました"
Write-Host "UI:  http://localhost:8095"
Write-Host "API: http://localhost:18795/health"
