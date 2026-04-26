$hookDir = ".git/hooks"
if (!(Test-Path $hookDir)) {
  Write-Host "ERROR: .git/hooks not found. Run this at repository root."
  exit 1
}

$hook = @'
#!/bin/bash
bash scripts/enforce_guardrails.sh
'@

Set-Content -Path "$hookDir/pre-commit" -Value $hook -Encoding UTF8
Write-Host "Installed pre-commit hook."
