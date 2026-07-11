param(
    [string]$InstallRoot = 'G:\moldflow_bridge',
    [string]$BindHost = '100.98.133.40',
    [int]$Port = 8765,
    [string]$AllowedRemoteAddress = '100.119.18.40'
)

$ErrorActionPreference = 'Stop'
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $InstallRoot '.venv\Scripts\python.exe'

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot 'work') | Out-Null
Copy-Item -Force (Join-Path $SourceRoot 'moldflow_mcp_server.py') $InstallRoot
Copy-Item -Force (Join-Path $SourceRoot 'check_synergy_com.vbs') $InstallRoot
Copy-Item -Force (Join-Path $SourceRoot 'requirements-mcp.txt') $InstallRoot
Copy-Item -Force (Join-Path $SourceRoot 'start_moldflow_mcp.ps1') $InstallRoot
Copy-Item -Force (Join-Path $SourceRoot 'mcp_smoke_client.py') $InstallRoot

if (-not (Test-Path $VenvPython)) {
    py -3 -m venv (Join-Path $InstallRoot '.venv')
}
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $InstallRoot 'requirements-mcp.txt')

$envFile = Join-Path $InstallRoot 'moldflow_mcp.env.ps1'
@"
`$env:MOLDFLOW_MCP_HOST='$BindHost'
`$env:MOLDFLOW_MCP_PORT='$Port'
`$env:MOLDFLOW_WORK_ROOT='$InstallRoot\work'
"@ | Set-Content -Encoding UTF8 $envFile

$ruleName = 'Clawstack Moldflow MCP (Tailscale K10 only)'
Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP `
    -LocalPort $Port -RemoteAddress $AllowedRemoteAddress -Profile Any | Out-Null

Write-Output '[OK] Moldflow MCP files and Python environment installed.'
Write-Output "Start with: powershell -ExecutionPolicy Bypass -File $InstallRoot\start_moldflow_mcp.ps1"
