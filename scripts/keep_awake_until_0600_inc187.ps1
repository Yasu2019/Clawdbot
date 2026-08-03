param(
    [datetime]$Until = ([datetime]::Today.AddHours(6))
)

$ErrorActionPreference = "Stop"
$statusPath = "D:\Clawdbot_Docker_20260125\data\state\lavie_mf_pipeline_monitor\keep_awake_until_0600_status.json"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Inc187PowerGuard {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

if ((Get-Date) -ge $Until) {
    $Until = $Until.AddDays(1)
}

try {
    while ((Get-Date) -lt $Until) {
        [void][Inc187PowerGuard]::SetThreadExecutionState([uint32]2147483649)
        $payload = [ordered]@{
            schema = "inc187.keep_awake.v1"
            updated_at = (Get-Date).ToString("o")
            state = "active"
            until = $Until.ToString("o")
            process_id = $PID
            display_required = $false
            system_required = $true
        }
        $payload | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
        Start-Sleep -Seconds 60
    }
}
finally {
    [void][Inc187PowerGuard]::SetThreadExecutionState([uint32]2147483648)
    $payload = [ordered]@{
        schema = "inc187.keep_awake.v1"
        updated_at = (Get-Date).ToString("o")
        state = "completed"
        until = $Until.ToString("o")
        process_id = $PID
        display_required = $false
        system_required = $false
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
