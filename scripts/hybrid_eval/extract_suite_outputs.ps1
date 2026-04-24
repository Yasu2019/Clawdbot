param(
  [string]$Phase0Dir = "",
  [string]$OutName = "suite_outputs.md"
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

$suitePath = Join-Path $Phase0Dir "suite_results.csv"
if (!(Test-Path $suitePath)) { throw "Missing suite_results.csv: $suitePath" }

$suite = Import-Csv -LiteralPath $suitePath -Encoding UTF8

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Suite Outputs")
$lines.Add("")
$lines.Add("- phase0_dir: $Phase0Dir")
$lines.Add("- generated_at: " + (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz"))
$lines.Add("")

foreach ($r in $suite) {
  $lines.Add("## Case $($r.case_no): $($r.prompt_template)")
  $lines.Add("")
  $lines.Add("- model: $($r.model)")
  $lines.Add("- elapsed_sec: $($r.elapsed_sec)")
  $lines.Add("- ok: $($r.ok)")
  if ($r.error) { $lines.Add("- error: $($r.error)") }
  $lines.Add("- run_dir: $($r.run_dir)")
  $lines.Add("")

  $rawPath = Join-Path $r.run_dir "ollama_raw.json"
  if (Test-Path $rawPath) {
    $raw = Read-Json $rawPath
    $resp = [string]$raw.response
    if (!$resp -and $raw.thinking) {
      $resp = "[NOTE] response empty; thinking present (model config?)"
    }
    $lines.Add('```')
    if ($resp) { $lines.Add($resp.Trim()) } else { $lines.Add("") }
    $lines.Add('```')
  } else {
    $lines.Add('```')
    $lines.Add("[missing ollama_raw.json]")
    $lines.Add('```')
  }
  $lines.Add("")
}

$outPath = Join-Path $Phase0Dir $OutName
Write-Utf8BomFile -Path $outPath -Text (($lines -join "`r`n") + "`r`n")
Write-Host $outPath
