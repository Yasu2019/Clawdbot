#Requires -Version 5.1
<#
.SYNOPSIS
  Allow inbound n8n :5679 from Tailscale satellites (LAVIE). Run elevated on K10.
#>
$ErrorActionPreference = "Stop"
$ruleName = "Clawstack n8n 5679 (Tailscale satellites)"
$existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Rule already exists: $ruleName"
} else {
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=5679 profile=Any
    Write-Host "[OK] Added firewall rule TCP 5679 profile=Any"
}
Write-Host "Test from LAVIE via Tailscale:"
Write-Host "  python scripts/k10_verify_satellite_node.py --node-id lavie --ip 100.87.244.46"
