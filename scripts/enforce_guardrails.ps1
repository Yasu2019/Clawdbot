$ErrorActionPreference = "Continue"

Write-Host "Checking protected file changes..."
$files = git diff --name-only
$protected = $files | Select-String -Pattern "app/views/layouts|app/views/shared|app/assets|app/javascript|config/routes.rb|\.env|config/master.key|config/credentials.yml.enc"

if ($protected) {
  Write-Host "ERROR: Protected files modified:"
  Write-Host $protected
  Write-Host "Create GitHub backup and confirm explicit approval before proceeding."
  exit 1
}

Write-Host "Guardrails OK"
