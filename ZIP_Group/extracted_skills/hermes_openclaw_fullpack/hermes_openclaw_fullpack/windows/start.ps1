$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (!(Test-Path ".env")) { Copy-Item ".env.example" ".env" }
docker compose -f configs/docker-compose.hermes-openclaw.yml up -d --build
python scripts/healthcheck.py
