Write-Host "Clawstack x OpenCode GO merge pre-check" -ForegroundColor Cyan
$required = @(".env", "configs/litellm/config.opencode-go.yaml", "policies/change_control_policy.md")
foreach ($f in $required) {
  if (Test-Path $f) { Write-Host "OK: $f" -ForegroundColor Green }
  else { Write-Host "MISSING: $f" -ForegroundColor Yellow }
}
Write-Host "Do not apply production changes before GitHub backup and human approval." -ForegroundColor Red
