$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
docker compose -f "$repoRoot/docker-compose.yml" -f "$repoRoot/docker-compose.addons.yml" up -d `
  immich_postgres immich_redis immich_machine_learning immich_server
