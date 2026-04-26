[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

Write-Host 'Health check...' -ForegroundColor Cyan
Invoke-RestMethod http://127.0.0.1:8765/health | ConvertTo-Json -Depth 5

Write-Host 'Run RC lowpass example...' -ForegroundColor Cyan
$ex = Invoke-RestMethod http://127.0.0.1:8765/examples/rc_lowpass
$body = @{ name = 'rc_lowpass_from_test_api'; netlist = $ex.netlist } | ConvertTo-Json -Depth 10
$res = Invoke-RestMethod -Uri http://127.0.0.1:8765/simulate -Method POST -Body $body -ContentType 'application/json'
$res | ConvertTo-Json -Depth 10
