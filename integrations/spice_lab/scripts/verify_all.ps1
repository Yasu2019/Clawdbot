[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'

Write-Host '=== OpenClaw SPICE Lab verify ===' -ForegroundColor Cyan

Write-Host '1) Docker service health'
try {
  Invoke-RestMethod http://127.0.0.1:8765/health | ConvertTo-Json -Depth 5
} catch {
  Write-Host "Docker API health failed: $_" -ForegroundColor Red
}

Write-Host '2) ngspice example'
try {
  $ex = Invoke-RestMethod http://127.0.0.1:8765/examples/rc_lowpass
  $body = @{ name = 'verify_rc_lowpass'; netlist = $ex.netlist } | ConvertTo-Json -Depth 10
  Invoke-RestMethod -Uri http://127.0.0.1:8765/simulate -Method POST -Body $body -ContentType 'application/json' | ConvertTo-Json -Depth 10
} catch {
  Write-Host "Simulation failed: $_" -ForegroundColor Red
}

Write-Host '3) LTspice path file'
$pathFile = Join-Path $env:USERPROFILE '.openclaw_spice_lab\ltspice_path.txt'
if (Test-Path $pathFile) {
  Write-Host "LTspice path: $((Get-Content $pathFile -Raw).Trim())" -ForegroundColor Green
} else {
  Write-Host 'LTspice path file not found. Run 00_windows_ltspice scripts if needed.' -ForegroundColor Yellow
}
