#Requires -Version 5.1
<#
.SYNOPSIS
  Periodic north star harvest + evolution apply (default 12h).
#>
[CmdletBinding()]
param(
    [int]$IntervalHours = 12,
    [int]$MaxPerDomain = 4
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$harvestScript = Join-Path $repoRoot "scripts\north_star_domain_harvest.py"
$applyScript = Join-Path $repoRoot "scripts\north_star_evolution_apply.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*start_north_star_evolution_watchdog*"
}
# T056: 自分以外の旧インスタンスを掃除して単一継続(従来は素通り=亡霊温存)
$others = @($existing | Where-Object { $_.ProcessId -ne $PID })
if ($others.Count -ge 1) {
    Write-Output "T056 cleanup: stopping $($others.Count) old instance(s): $($others.ProcessId -join ', ')"
    $others | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$stamp] north_star harvest start"
    python $harvestScript --max-per-domain $MaxPerDomain 2>&1 | Out-Host
    Write-Output "[$stamp] north_star evolution apply"
    python $applyScript 2>&1 | Out-Host
    Start-Sleep -Seconds ([Math]::Max(1, $IntervalHours) * 3600)
}
