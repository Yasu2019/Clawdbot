$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")

$folders = @(
  "ltspice\exported_waveforms",
  "ltspice\work",
  "wokwi\calibration",
  "node-red\exports",
  "logs"
)

foreach ($f in $folders) {
  $path = Join-Path $RootDir $f
  if (!(Test-Path $path)) {
    New-Item -ItemType Directory -Path $path | Out-Null
    Write-Host "Created: $path"
  } else {
    Write-Host "Exists: $path"
  }
}

Write-Host ""
Write-Host "Folder preparation complete." -ForegroundColor Cyan
