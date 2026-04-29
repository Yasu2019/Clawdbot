param(
  [string]$Prefix = "before-julia-worker"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$branch = "$Prefix-$timestamp"

Write-Host "Checking git repository..."
git status

Write-Host "Creating backup branch: $branch"
git branch $branch

Write-Host "Creating backup tag: $branch"
git tag $branch

Write-Host "Backup created."
Write-Host "Branch/Tag: $branch"
