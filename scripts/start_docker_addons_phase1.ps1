$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
docker compose -f "$repoRoot/docker-compose.yml" -f "$repoRoot/docker-compose.addons.yml" up -d `
  stirling_pdf actual_budget vikunja dashy ntfy
