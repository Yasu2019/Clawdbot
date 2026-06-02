#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap LAVIE for CAE fill video (pyvista + ffmpeg in tools/).
  Run after lavie_usb_pack sync or from lavie_setup.
#>
$ErrorActionPreference = "Stop"
$Repo = if ($env:LAVIE_REPO_ROOT) { $env:LAVIE_REPO_ROOT } else { "C:\lavie_usb_pack" }
$Tools = Join-Path $Repo "tools"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

$Py = "C:\Users\ysuzu\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

Write-Host "[bootstrap] pip pyvista matplotlib..."
& $Py -m pip install --upgrade pip -q 2>$null
& $Py -m pip install pyvista matplotlib -q
& $Py -c "import pyvista; print('[OK] pyvista', pyvista.__version__)"

$Ff = Join-Path $Tools "ffmpeg.exe"
if (-not (Test-Path $Ff)) {
    Write-Host "[bootstrap] ffmpeg.exe missing in tools - K10 pull path still works"
    exit 0
}
& $Ff -version 2>&1 | Select-Object -First 1
Write-Host "[OK] ffmpeg at $Ff"
