Param(
  [string]$TargetRoot = "D:\Clawdbot_Docker_20260125\ace_step_stack"
)

$ErrorActionPreference = "Stop"
Push-Location $TargetRoot
try {
  docker compose --env-file .env up -d
  docker compose ps
} finally {
  Pop-Location
}
