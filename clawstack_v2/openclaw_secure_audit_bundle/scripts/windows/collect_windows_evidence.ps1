$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "evidence\windows_audit_$ts.txt"
New-Item -ItemType Directory -Force -Path evidence | Out-Null
"# Windows Evidence $ts" | Out-File $out -Encoding utf8
"## WSL List" | Out-File $out -Append -Encoding utf8
wsl -l -v | Out-File $out -Append -Encoding utf8
"## Docker Desktop Processes" | Out-File $out -Append -Encoding utf8
Get-Process | Where-Object {$_.ProcessName -like "*Docker*"} | Select-Object ProcessName,Id,Path | Format-Table | Out-File $out -Append -Encoding utf8
"saved: $out"
