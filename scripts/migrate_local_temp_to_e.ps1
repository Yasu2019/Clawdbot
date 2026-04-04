$ErrorActionPreference = 'Stop'

$sourceTemp = 'C:\Users\yasu\AppData\Local\Temp'
$targetRoot = 'E:\ClawstackData'
$targetTemp = Join-Path $targetRoot 'LocalTemp'
$statusPath = 'D:\Clawdbot_Docker_20260125\data\workspace\local_temp_migration_status.json'

function Get-DriveSnapshot {
    param([string]$Name)
    $drive = Get-PSDrive -Name $Name -ErrorAction Stop
    return @{
        free_gb = [math]::Round(($drive.Free / 1GB), 2)
        used_gb = [math]::Round(($drive.Used / 1GB), 2)
    }
}

function Set-UserEnvVar {
    param([string]$Name, [string]$Value)
    [Environment]::SetEnvironmentVariable($Name, $Value, 'User')
    Set-ItemProperty -Path 'HKCU:\Environment' -Name $Name -Value $Value
    Set-Item -Path "Env:$Name" -Value $Value
}

New-Item -ItemType Directory -Force -Path $targetTemp | Out-Null

$status = [ordered]@{
    updatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss K')
    service = 'local_temp_migration'
    sourceTemp = $sourceTemp
    targetTemp = $targetTemp
    before = @{
        c = Get-DriveSnapshot -Name 'C'
        e = Get-DriveSnapshot -Name 'E'
        tempEnv = $env:TEMP
        tmpEnv = $env:TMP
    }
}

Set-UserEnvVar -Name 'TEMP' -Value $targetTemp
Set-UserEnvVar -Name 'TMP' -Value $targetTemp

$robocopyLog = Join-Path $targetRoot 'local_temp_migration_robocopy.log'
$robocopyArgs = @(
    $sourceTemp,
    $targetTemp,
    '/E',
    '/MOVE',
    '/R:1',
    '/W:1',
    '/NFL',
    '/NDL',
    '/NP',
    '/XJ',
    "/LOG:$robocopyLog"
)

$robocopyExitCode = $null
try {
    $robocopyProc = Start-Process -FilePath 'robocopy.exe' -ArgumentList $robocopyArgs -Wait -PassThru -WindowStyle Hidden
    $robocopyExitCode = $robocopyProc.ExitCode
} catch {
    $status.robocopyError = $_.Exception.Message
}

$oldTempInfo = @{
    exists = (Test-Path $sourceTemp)
    attributes = if (Test-Path $sourceTemp) { (Get-Item -LiteralPath $sourceTemp -Force).Attributes.ToString() } else { 'missing' }
}

$status.after = @{
    c = Get-DriveSnapshot -Name 'C'
    e = Get-DriveSnapshot -Name 'E'
    tempEnv = [Environment]::GetEnvironmentVariable('TEMP', 'User')
    tmpEnv = [Environment]::GetEnvironmentVariable('TMP', 'User')
}
$status.robocopyExitCode = $robocopyExitCode
$status.robocopyLog = $robocopyLog
$status.oldTempInfo = $oldTempInfo
$status.note = 'TEMP/TMP were redirected to E:\\ClawstackData\\LocalTemp. Locked files may remain in C:\\Users\\yasu\\AppData\\Local\\Temp until apps restart.'

$json = $status | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($statusPath, $json, [System.Text.Encoding]::UTF8)
Write-Output $json
