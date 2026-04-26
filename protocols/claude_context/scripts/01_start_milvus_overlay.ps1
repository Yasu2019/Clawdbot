$composeFile = ".\compose\docker-compose.claude-context.yml"
if (!(Test-Path $composeFile)) {
  Write-Error "Run this script from the root of openclaw_claude_context_protocol."
  exit 1
}

docker compose -f $composeFile up -d
Start-Sleep -Seconds 10
docker ps --filter "name=openclaw_milvus" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
