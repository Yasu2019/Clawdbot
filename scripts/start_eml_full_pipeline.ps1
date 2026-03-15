$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$preprocess = Join-Path $repoRoot "scripts\start_eml_preprocess_for_paperless.ps1"
$enrich = Join-Path $repoRoot "scripts\start_eml_enrich_for_paperless.ps1"

$limit = if ($args.Count -gt 0) { [int]$args[0] } else { 0 }

if ($limit -gt 0) {
  powershell -ExecutionPolicy Bypass -File $preprocess $limit
  powershell -ExecutionPolicy Bypass -File $enrich $limit
} else {
  powershell -ExecutionPolicy Bypass -File $preprocess
  powershell -ExecutionPolicy Bypass -File $enrich
}
