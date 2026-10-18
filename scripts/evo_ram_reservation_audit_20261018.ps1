[CmdletBinding()]
param([string]$OutputPath)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$installed=[double]((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum)
$os=Get-CimInstance Win32_OperatingSystem
$adapters=@(Get-CimInstance Win32_VideoController | ForEach-Object {
    $device=Get-ItemProperty -LiteralPath ('HKLM:\SYSTEM\CurrentControlSet\Enum\'+$_.PNPDeviceID)
    $key='HKLM:\SYSTEM\CurrentControlSet\Control\Class\'+$device.Driver
    $properties=Get-ItemProperty -LiteralPath $key
    $raw=$properties.'HardwareInformation.qwMemorySize'
    $bytes=if($raw -is [byte[]] -and $raw.Length -eq 8){[BitConverter]::ToUInt64($raw,0)}elseif($raw -is [ValueType]){$raw}else{$null}
    [pscustomobject]@{Name=$_.Name;Status=$_.Status;ActiveDeviceDriverKey=$device.Driver;DedicatedMemoryBytesReported=$bytes}
})
$boot=@(& bcdedit.exe /enum all 2>&1)
$bootExit=$LASTEXITCODE
$limits=@($boot | Where-Object {"$_" -match '^\s*(truncatememory|removememory|maxmem|numproc|badmemorylist)\s+'})
$r=[ordered]@{
    observed_at=(Get-Date -Format o)
    host=$env:COMPUTERNAME
    source='Live CIM DIMMs/OS/video PNP mapping, current display driver registry, complete BCD enumeration'
    installed_dimm_bytes=$installed
    windows_visible_bytes=[double]$os.TotalVisibleMemorySize*1024
    installed_minus_visible_bytes=$installed-[double]$os.TotalVisibleMemorySize*1024
    bios=(Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion)
    current_display_adapters=$adapters
    boot_query_exit_code=$bootExit
    explicit_boot_memory_limits=$limits
    conclusion='Current adapter memory plus OS-visible RAM supports GPU/UMA reservation as the primary explanation. BIOS setting itself has not been inspected; verify before changing. Never use an arbitrary inactive adapter registry key or 32-bit AdapterRAM as installed memory evidence.'
    changes_performed=@()
}
$json=$r|ConvertTo-Json -Depth 6
if($OutputPath){[IO.File]::WriteAllText($OutputPath,$json,[Text.UTF8Encoding]::new($false))}
$json
