$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$paths = @(
  "clawstack_v2/data/stirling_pdf/trainingData",
  "clawstack_v2/data/stirling_pdf/extraConfigs",
  "clawstack_v2/data/changedetection",
  "clawstack_v2/data/actual_budget",
  "clawstack_v2/data/vikunja/files",
  "clawstack_v2/data/vikunja/db",
  "clawstack_v2/data/immich/library",
  "clawstack_v2/data/ntfy/cache",
  "clawstack_v2/data/ntfy/config"
)

foreach ($relative in $paths) {
  New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot $relative) | Out-Null
}

$services = @(
  "stirling_pdf",
  "browserless",
  "changedetection",
  "actual_budget",
  "vikunja",
  "ntfy",
  "dashy",
  "immich_postgres",
  "immich_redis",
  "immich_machine_learning",
  "immich_server"
)

docker compose -f "$repoRoot/docker-compose.yml" -f "$repoRoot/docker-compose.addons.yml" up -d @services
