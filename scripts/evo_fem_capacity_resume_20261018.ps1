param([Parameter(Mandatory=$true)][ValidateSet('P1r43f','P1r44f')][string]$Case,
      [ValidateSet('initial','after-reboot-2238')][string]$Attempt='initial')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$os=Get-CimInstance Win32_OperatingSystem
if([double]$os.TotalVisibleMemorySize*1024 -lt 56GB){throw 'Expected expanded Windows RAM unavailable; preserve stopped cases.'}
$video=Get-CimInstance Win32_VideoController | Where-Object Name -match '8060S'
if(@($video).Count -ne 1){throw 'Expected Radeon adapter unavailable'}
$dev=Get-ItemProperty -LiteralPath ('HKLM:\SYSTEM\CurrentControlSet\Enum\'+$video.PNPDeviceID)
$gpu=Get-ItemProperty -LiteralPath ('HKLM:\SYSTEM\CurrentControlSet\Control\Class\'+$dev.Driver)
$bytes=$gpu.'HardwareInformation.qwMemorySize'
if($bytes -is [byte[]]){$bytes=[BitConverter]::ToUInt64($bytes,0)}
if($bytes -ne 4GB){throw 'GPU reservation not4GiB; do not resume automatically.'}
& wsl.exe -d EVO-OpenFOAM-20261018 -u root -- python3 /mnt/c/Users/Suzuki/evo_fem_capacity_resume_20261018.py --case $Case --attempt $Attempt
exit $LASTEXITCODE
