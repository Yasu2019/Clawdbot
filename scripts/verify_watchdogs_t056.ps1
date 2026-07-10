# T056一括修正の構文検証(ホスト実行): 全start_*.ps1をPowerShellパーサで検査
$errs = 0
Get-ChildItem "$PSScriptRoot\start_*.ps1" | ForEach-Object {
    $tokens = $null; $parseErrs = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrs) | Out-Null
    if ($parseErrs.Count -gt 0) {
        $errs++
        Write-Output "[NG] $($_.Name): $($parseErrs[0].Message)"
    }
}
if ($errs -eq 0) { Write-Output "[OK] all start_*.ps1 parse clean (T056 migration verified)" }
else { Write-Output "[NG] $errs file(s) failed - restore from backups\watchdog_t056_20260710\" }
