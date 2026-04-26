$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$safeCurate = Join-Path $repoRoot "data\workspace\safe_brv_curate.py"
$summary = "Summarize important development decisions, operational fixes, and durable project knowledge from today's work in D:\\Clawdbot_Docker_20260125."

python $safeCurate $summary
