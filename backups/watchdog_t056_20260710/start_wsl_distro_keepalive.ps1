$scriptPath = Join-Path $PSScriptRoot "..\data\workspace\wsl_distro_keepalive.py"
$resolvedScript = [System.IO.Path]::GetFullPath($scriptPath)

$existing = Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^python' -and $_.CommandLine -like "*wsl_distro_keepalive.py*" }

if ($existing) {
  Write-Output "WSL distro keepalive already running."
  exit 0
}

Start-Process python -ArgumentList @($resolvedScript, "--distro", "Ubuntu", "--poll-seconds", "30") -WindowStyle Hidden
Write-Output "WSL distro keepalive started."
