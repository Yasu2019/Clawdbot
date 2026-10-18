[CmdletBinding()]
param(
    [string]$Distro = 'EVO-OpenFOAM-20261018',
    [ValidateRange(2,30)][int]$SampleSeconds = 4,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$cpu = @(Get-CimInstance Win32_Processor)
$os = Get-CimInstance Win32_OperatingSystem
$installed = [double]((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum)
$visible = [double]$os.TotalVisibleMemorySize * 1024
$logical = [int](($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum)
$before = @{}
Get-Process -Name vmmemWSL -ErrorAction SilentlyContinue | ForEach-Object { $before[$_.Id] = $_.CPU }
$clock = [Diagnostics.Stopwatch]::StartNew()
Start-Sleep -Seconds $SampleSeconds
$clock.Stop()
$vmSeconds = 0.0
$sameProcess = $false
Get-Process -Name vmmemWSL -ErrorAction SilentlyContinue | ForEach-Object {
    if ($before.ContainsKey($_.Id)) {
        $vmSeconds += [math]::Max(0, $_.CPU - $before[$_.Id])
        $sameProcess = $true
    }
}
$perf = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total'
$configPath = Join-Path $env:USERPROFILE '.wslconfig'
$config = if (Test-Path -LiteralPath $configPath) { Get-Content -LiteralPath $configPath -Raw } else { '' }
# Fixed read-only commands; no arbitrary case commands and no solver lifecycle changes.
$linux = @(& wsl.exe -d $Distro -- sh -c 'date -Is; getconf _NPROCESSORS_ONLN; cat /proc/meminfo; ps -eo pid,comm,pcpu,nlwp --sort=-pcpu | head -8' 2>&1)
$linuxExit = $LASTEXITCODE
$warnings = @()
if ($installed -le 0) { $warnings += 'Installed DIMM capacity unavailable; do not infer installed capacity from OS-visible RAM.' }
if ($installed -gt 0 -and ($installed - $visible) -gt [math]::Max(2GB, $installed * 0.1)) {
    $warnings += 'Installed and OS-visible RAM differ materially. GPU/firmware reservation, boot limits and SMBIOS accuracy require investigation; cause unconfirmed.'
}
if ($linuxExit -ne 0) { $warnings += 'WSL live probe failed; saved status cannot substitute for current readiness.' }
$normalized = if ($sameProcess -and $logical -gt 0) { [math]::Round(100 * $vmSeconds / $clock.Elapsed.TotalSeconds / $logical, 2) } else { $null }
$report = [ordered]@{
    schema_version = 1
    observed_at = (Get-Date -Format o)
    host = $env:COMPUTERNAME
    source = 'Live CIM DIMMs/OS/CPU, PerfOS Processor, elapsed vmmemWSL CPU time and WSL procfs'
    installed_dimm_bytes = $installed
    windows_visible_bytes = $visible
    windows_available_bytes_at_probe_start = [double]$os.FreePhysicalMemory * 1024
    installed_minus_visible_bytes = $installed - $visible
    physical_cores = ($cpu | Measure-Object NumberOfCores -Sum).Sum
    logical_processors = $logical
    windows_processor_time_percent = $perf.PercentProcessorTime
    wmi_load_percentage_incomparable_snapshot = @($cpu | Select-Object -ExpandProperty LoadPercentage)
    wsl_cpu_time_normalized_to_host_percent = $normalized
    cpu_sample_seconds = [math]::Round($clock.Elapsed.TotalSeconds, 3)
    wsl_config = @($config -split '\r?\n' | Where-Object { $_ -match '^\s*(memory|processors|swap)\s*=' })
    wsl_live_exit_code = $linuxExit
    wsl_live = @($linux | ForEach-Object { "$_" })
    warnings = $warnings
    additional_fem_dispatch = if ($warnings.Count) { 'hold_for_resource_reconciliation' } else { 'requires_case_memory_cpu_budget_and_verified_checkpoint_preflight' }
    notes = 'Read-only probe, not a scheduler. Logical threads share physical cores; configured thread count is not CPU utilization. WSL available memory overlaps host accounting and must not be added to Windows available RAM. No reboot or configuration change.'
}
$json = $report | ConvertTo-Json -Depth 6
if ($OutputPath) { [IO.File]::WriteAllText($OutputPath, $json, [Text.UTF8Encoding]::new($false)) }
$json
