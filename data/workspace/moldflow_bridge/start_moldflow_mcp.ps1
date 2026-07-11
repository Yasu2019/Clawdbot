param([switch]$Hidden)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root 'moldflow_mcp.env.ps1')
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Server = Join-Path $Root 'moldflow_mcp_server.py'
$Log = Join-Path $Root 'moldflow_mcp.log'

if ($Hidden) {
    Start-Process -FilePath $Python -ArgumentList @($Server) -WorkingDirectory $Root `
        -RedirectStandardOutput $Log -RedirectStandardError (Join-Path $Root 'moldflow_mcp.error.log') `
        -WindowStyle Hidden
    Write-Output '[OK] Moldflow MCP started in background.'
} else {
    & $Python $Server
}
