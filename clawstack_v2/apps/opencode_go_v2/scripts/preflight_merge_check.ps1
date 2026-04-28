Write-Host "=== OpenCode GO Clawstack Fusion v2 preflight ==="
$checks = @("opencode_go_clawstack_honki", "docker-compose.yml", ".git")
foreach ($c in $checks) {
  if (Test-Path $c) { Write-Host "OK: found $c" } else { Write-Host "WARN: not found $c" }
}
Write-Host "Recommended: git checkout -b feature/opencode-go-fusion-v2"
Write-Host "Do not overwrite existing configs automatically."
