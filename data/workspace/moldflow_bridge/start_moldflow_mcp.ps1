param([switch]$Hidden)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root 'moldflow_mcp.env.ps1')
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Server = Join-Path $Root 'moldflow_mcp_server.py'
$Log = Join-Path $Root 'moldflow_mcp.log'
$Port = [int]$env:MOLDFLOW_MCP_PORT

$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($listener) {
    Write-Output "[OK] Moldflow MCP already listening on port $Port (PID $($listener.OwningProcess))."
    exit 0
}

if ($Hidden) {
    Start-Process -FilePath $Python -ArgumentList @($Server) -WorkingDirectory $Root `
        -RedirectStandardOutput $Log -RedirectStandardError (Join-Path $Root 'moldflow_mcp.error.log') `
        -WindowStyle Hidden
    Write-Output '[OK] Moldflow MCP started in background.'
} else {
    & $Python $Server
}
