$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\eml_preprocess_for_paperless.py"

$limit = if ($args.Count -gt 0) { [int]$args[0] } else { 0 }
$limitArgs = @()
if ($limit -gt 0) {
  $limitArgs = @("--limit", "$limit")
}

$dryRunArgs = @()
if ($args.Count -gt 1 -and "$($args[1])" -eq "--dry-run") {
  $dryRunArgs = @("--dry-run")
}

python $scriptPath @limitArgs @dryRunArgs
