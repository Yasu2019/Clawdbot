# UE5 guard: read-only warning and detection helper
$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $PSScriptRoot "..\reports\no_ue5_guard_$ts.txt"

"UE5 Guard Check - $ts" | Out-File $out -Encoding utf8
"Policy: UE5 is not allowed in this protocol." | Out-File $out -Append -Encoding utf8

$commonPaths = @(
  "C:\Program Files\Epic Games",
  "D:\Epic Games",
  "D:\UnrealEngine",
  "C:\UnrealEngine"
)

foreach ($path in $commonPaths) {
  if (Test-Path $path) {
    "Found possible UE/Epic path: $path" | Out-File $out -Append -Encoding utf8
  } else {
    "Not found: $path" | Out-File $out -Append -Encoding utf8
  }
}

"Do not clone, build, or install UE5 for this workflow." | Out-File $out -Append -Encoding utf8
Write-Host "UE5 guard check complete: $out"
