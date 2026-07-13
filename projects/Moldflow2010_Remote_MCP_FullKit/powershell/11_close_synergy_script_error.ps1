param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = "Stop"
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MoldflowWindowNative {
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr childAfter, string className, string title);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
}
"@

$after = [IntPtr]::Zero
$matched = [IntPtr]::Zero
while ($true) {
    $window = [MoldflowWindowNative]::FindWindowEx([IntPtr]::Zero, $after, "Internet Explorer_TridentDlgFrame", $null)
    if ($window -eq [IntPtr]::Zero) { break }
    [uint32]$owner = 0
    [void][MoldflowWindowNative]::GetWindowThreadProcessId($window, [ref]$owner)
    if ($owner -eq $ProcessId) { $matched = $window; break }
    $after = $window
}

@{ process_id = $ProcessId; handle = $matched.ToInt64() } |
    ConvertTo-Json -Compress | Set-Content -LiteralPath $OutputPath -Encoding UTF8
if ($matched -eq [IntPtr]::Zero) { exit 2 }
[void][MoldflowWindowNative]::PostMessage($matched, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
