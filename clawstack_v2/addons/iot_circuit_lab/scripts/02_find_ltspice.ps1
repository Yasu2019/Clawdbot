$ErrorActionPreference = "Continue"

$candidates = @(
  "$env:LOCALAPPDATA\Programs\ADI\LTspice\LTspice.exe",
  "$env:ProgramFiles\ADI\LTspice\LTspice.exe",
  "${env:ProgramFiles(x86)}\ADI\LTspice\LTspice.exe",
  "$env:LOCALAPPDATA\Programs\LTC\LTspiceXVII\XVIIx64.exe",
  "$env:ProgramFiles\LTC\LTspiceXVII\XVIIx64.exe",
  "${env:ProgramFiles(x86)}\LTC\LTspiceXVII\XVIIx64.exe"
)

Write-Host "Searching LTspice executable candidates..." -ForegroundColor Cyan

$found = @()
foreach ($c in $candidates) {
  if ($c -and (Test-Path $c)) {
    $found += $c
    Write-Host "[FOUND] $c" -ForegroundColor Green
  } else {
    Write-Host "[MISS ] $c"
  }
}

Write-Host ""
if ($found.Count -eq 0) {
  Write-Host "LTspice executable was not found in common paths." -ForegroundColor Yellow
  Write-Host "If installed, add your LTspice path manually to Portal card or scripts."
} else {
  Write-Host "Use this path for Portal/OpenClaw/Codex handoff:" -ForegroundColor Cyan
  $found | ForEach-Object { Write-Host $_ }
}
