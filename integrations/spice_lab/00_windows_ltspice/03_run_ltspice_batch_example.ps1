# Run LTspice in batch mode using the detected executable.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$pathFile = Join-Path $env:USERPROFILE '.openclaw_spice_lab\ltspice_path.txt'
if (!(Test-Path $pathFile)) {
  Write-Host 'ltspice_path.txt がありません。先に 02_check_ltspice_cli.ps1 を実行してください。' -ForegroundColor Red
  exit 1
}
$lt = (Get-Content $pathFile -Raw).Trim()
if (!(Test-Path $lt)) {
  Write-Host "LTspice実行ファイルが存在しません: $lt" -ForegroundColor Red
  exit 1
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cir = Join-Path $here 'examples\rc_lowpass_ltspice.cir'
$outDir = Join-Path $here 'runs\ltspice_example'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item $cir (Join-Path $outDir 'rc_lowpass_ltspice.cir') -Force
Push-Location $outDir

Write-Host 'LTspice batch simulationを実行します...' -ForegroundColor Cyan
Write-Host "LTspice: $lt"
Write-Host "Circuit:  $cir"
& $lt -b '.\rc_lowpass_ltspice.cir'
$code = $LASTEXITCODE
Pop-Location

Write-Host "ExitCode: $code"
Write-Host "出力フォルダ: $outDir"
Get-ChildItem $outDir | Format-Table Name,Length,LastWriteTime
