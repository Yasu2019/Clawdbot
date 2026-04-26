Write-Host "=== OpenClaw Workspace Agents Preflight ==="
$ports = @(18080,18789,5679,6333)
foreach ($p in $ports) {
  $used = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
  if ($used) { Write-Host "Port $p: USED" -ForegroundColor Yellow } else { Write-Host "Port $p: free" -ForegroundColor Green }
}
Write-Host "Check docker compose files manually before merge."
