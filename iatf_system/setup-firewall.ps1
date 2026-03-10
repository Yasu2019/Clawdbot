# 管理者権限でファイアウォールのルールを追加
$ruleName = "HTTP 80 for Rails"
$ruleExists = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if (-not $ruleExists) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80
    Write-Host "Firewall rule for port 80 has been added successfully."
} else {
    Write-Host "Firewall rule for port 80 already exists."
}
