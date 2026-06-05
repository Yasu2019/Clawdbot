$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root 'data\workspace\api_cost_report.py'

# Update quota stats first
$QuotaScript = Join-Path $Root 'scripts\update_api_quota_status.py'
python $QuotaScript
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Failed to update quota status, but continuing to generate cost report..."
}
python $Script --send-telegram
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
