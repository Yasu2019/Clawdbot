param(
  [string]$Phase0Dir = ""
)

$ErrorActionPreference = "Stop"

function Get-LatestPhase0Dir() {
  $root = "tmp/foundrylocal_phase0"
  if (!(Test-Path $root)) { return $null }
  return (Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
}

if (!$Phase0Dir) { $Phase0Dir = Get-LatestPhase0Dir }
if (!$Phase0Dir) { throw "Phase0Dir not found." }
if (!(Test-Path $Phase0Dir)) { throw "Phase0Dir not found: $Phase0Dir" }

$suitePath = Join-Path $Phase0Dir "suite_results.csv"
if (!(Test-Path $suitePath)) { throw "Missing suite_results.csv: $suitePath" }

$suite = Import-Csv -LiteralPath $suitePath -Encoding UTF8

$rows = @()
$i = 0
foreach ($r in $suite) {
  $i++
  $task = [string]$r.prompt_template
  $task = $task -replace '^\d\d_', ''
  $task = $task -replace '\.txt$', ''

  $rows += [pscustomobject]@{
    試験No = $i
    日付 = [string]$r.date
    タスク分類 = $task
    入力概要 = ""
    モデル = [string]$r.model
    返答開始体感 = ""
    完了速度 = [string]$r.elapsed_sec
    品質 = ""
    安定性 = if ([string]$r.ok -eq "True") { "OK" } else { "NG" }
    備考 = [string]$r.error
    run_dir = [string]$r.run_dir
  }
}

$outPath = Join-Path $Phase0Dir "08_評価記録シート_auto.csv"
$rows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host $outPath

