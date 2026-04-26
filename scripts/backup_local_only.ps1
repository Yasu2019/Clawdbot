param(
  [string]$Message = "local backup before AI change"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$branch = "backup/ai-local-$timestamp"

git status --short
try {
  git add -A
  git commit -m $Message
} catch {
  Write-Host "No commit created or commit failed. Continuing to branch backup."
}

git branch $branch
Write-Host "LOCAL_BACKUP_BRANCH=$branch"
