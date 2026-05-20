$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "data\workspace\pdca_feedback_phase1.py"

python $Script refresh
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
