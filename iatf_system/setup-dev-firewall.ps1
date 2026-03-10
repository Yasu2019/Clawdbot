# 管理者権限で開発用ポート（3000, 1880）を開放
$rules = @(
    @{ Name = "Rails Dev (3000)"; Port = 3000 },
    @{ Name = "Node-RED (1880)"; Port = 1880 }
)

foreach ($rule in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $rule.Port
        Write-Host "Added firewall rule for port $($rule.Port) ($($rule.Name))"
    } else {
        Write-Host "Firewall rule for port $($rule.Port) already exists."
    }
}
