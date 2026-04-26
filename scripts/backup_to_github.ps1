param(
  [string]$Message = "backup before AI change"
)

$ErrorActionPreference = "Continue"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$current = git rev-parse --abbrev-ref HEAD
$backupBranch = "backup/ai-$timestamp"

Write-Host "Current branch: $current"
Write-Host "Creating backup commit..."

git add -A
$commitResult = git commit -m $Message 2>&1
Write-Host $commitResult

Write-Host "Creating backup branch: $backupBranch"
git branch $backupBranch

Write-Host "Pushing current branch..."
git push origin $current
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARNING: push current branch failed."
}

Write-Host "Pushing backup branch..."
git push origin $backupBranch
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARNING: GitHub push failed. Local backup branch exists: $backupBranch"
  exit 2
}

Write-Host "GITHUB_BACKUP_BRANCH=$backupBranch"
