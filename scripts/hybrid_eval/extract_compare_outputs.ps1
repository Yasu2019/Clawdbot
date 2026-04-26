param(
  [string]$Phase0Dir = "",
  [string]$OutName = "compare_outputs.md"
)

$ErrorActionPreference = "Stop"

function Get-LatestPhase0Dir() {
  $root = "tmp/foundrylocal_phase0"
  if (!(Test-Path $root)) { return $null }
  return (Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
}

function Read-Json([string]$Path) {
  return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-Utf8BomFile([string]$Path, [string]$Text) {
  $dir = Split-Path -Parent $Path
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $Text | Out-File -LiteralPath $Path -Encoding UTF8
}

if (!$Phase0Dir) { $Phase0Dir = Get-LatestPhase0Dir }
if (!$Phase0Dir) { throw "Phase0Dir not found." }
if (!(Test-Path $Phase0Dir)) { throw "Phase0Dir not found: $Phase0Dir" }

$comparePath = Join-Path $Phase0Dir "compare_results.csv"
if (!(Test-Path $comparePath)) { throw "Missing compare_results.csv: $comparePath" }
$rows = Import-Csv -LiteralPath $comparePath -Encoding UTF8

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Compare Outputs")
$lines.Add("")
$lines.Add("- phase0_dir: $Phase0Dir")
$lines.Add("- generated_at: " + (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz"))
$lines.Add("")

foreach ($r in $rows) {
  $lines.Add("## Case $($r.case_no): $($r.prompt_file)")
  $lines.Add("")
  $lines.Add("- elapsed_sec: $($r.elapsed_sec)")
  $lines.Add("- run_dir: $($r.run_dir)")
  if ($r.error) { $lines.Add("- error: $($r.error)") }
  $lines.Add("")

  $oPath = Join-Path $r.run_dir "ollama_raw.json"
  $fPath = Join-Path $r.run_dir "foundry_raw.json"

  $o = if (Test-Path $oPath) { Read-Json $oPath } else { $null }
  $f = if (Test-Path $fPath) { Read-Json $fPath } else { $null }

  $lines.Add("### Ollama")
  $lines.Add("")
  $lines.Add('```')
  if ($o -and $o.response) { $lines.Add(([string]$o.response).Trim()) } else { $lines.Add("[missing/empty]") }
  $lines.Add('```')
  $lines.Add("")

  $lines.Add("### Foundry")
  $lines.Add("")
  $lines.Add('```')
  if ($f -and $f.stdout) { $lines.Add(([string]$f.stdout).Trim()) } else { $lines.Add("[missing/empty]") }
  $lines.Add('```')
  $lines.Add("")
}

$outPath = Join-Path $Phase0Dir $OutName
Write-Utf8BomFile -Path $outPath -Text (($lines -join "`r`n") + "`r`n")
Write-Host $outPath
