# Detect LTspice executable path.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$candidates = @(
  "$env:ProgramFiles\ADI\LTspice\LTspice.exe",
  "$env:ProgramFiles\LTC\LTspiceXVII\XVIIx64.exe",
  "$env:LOCALAPPDATA\Programs\ADI\LTspice\LTspice.exe",
  "$env:LOCALAPPDATA\LTspice\LTspice.exe",
  "$env:ProgramFiles(x86)\LTC\LTspiceXVII\XVIIx64.exe",
  "$env:ProgramFiles(x86)\LTC\LTspiceIV\scad3.exe"
)

$found = @()
foreach ($p in $candidates) {
  if ($p -and (Test-Path $p)) { $found += $p }
}

# Fallback: limited search in common folders
$searchRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA) | Where-Object { $_ -and (Test-Path $_) }
foreach ($root in $searchRoots) {
  try {
    Get-ChildItem -Path $root -Filter 'LTspice.exe' -Recurse -ErrorAction SilentlyContinue -Depth 4 | ForEach-Object { $found += $_.FullName }
    Get-ChildItem -Path $root -Filter 'XVIIx64.exe' -Recurse -ErrorAction SilentlyContinue -Depth 4 | ForEach-Object { $found += $_.FullName }
  } catch {}
}

$found = $found | Select-Object -Unique
$outDir = Join-Path $env:USERPROFILE '.openclaw_spice_lab'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outFile = Join-Path $outDir 'ltspice_path.txt'

if ($found.Count -eq 0) {
  Write-Host 'LTspice実行ファイルが見つかりませんでした。' -ForegroundColor Red
  Write-Host '公式ページからインストール後、再実行してください。'
  exit 1
}

$selected = $found[0]
$selected | Set-Content -Path $outFile -Encoding UTF8
Write-Host 'LTspice実行ファイルを検出しました:' -ForegroundColor Green
Write-Host $selected
Write-Host "保存先: $outFile"

try {
  & $selected -? | Out-Null
} catch {
  Write-Host 'ヘルプ表示は取得できませんでしたが、実行ファイルの存在は確認済みです。' -ForegroundColor Yellow
}
